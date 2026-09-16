// #1305 (ISSUE1305HOOKSCOPE): the tracked .claude/settings.json is the
// AUTHORITATIVE registration surface for the main agent's fleet hooks. The
// scaffold refuses to write them anywhere else (hook-scope-main-refusal
// pins that), so if an entry silently falls out of this file, nothing
// re-adds it -- the hook just stops firing. This anchor makes such a drop
// loud: the full expected set is spelled out, per event.
//
// Portability is part of the contract: every command must resolve through
// $CLAUDE_PROJECT_DIR (the file ships to every install), and the WebFetch
// egress gate must keep its fail-CLOSED preamble -- the user-global variant
// pinned a machine-local node path, which is exactly what broke in the
// owner's own sessions (#1305) and what a "simplifying" edit would
// reintroduce.
import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { join } from 'node:path'

const ROOT = join(__dirname, '..', '..')
const SETTINGS_PATH = join(ROOT, '.claude', 'settings.json')

interface HookEntry { matcher?: string; hooks?: Array<{ type?: string; command?: string; timeout?: number }> }
type Hooks = Record<string, HookEntry[]>

const settings = JSON.parse(readFileSync(SETTINGS_PATH, 'utf-8')) as { hooks?: Hooks }
const hooks: Hooks = settings.hooks ?? {}

// The full expected registration: event -> script basenames (order-free).
// A change here is a REVIEWED decision about what runs in the main session,
// never a side effect.
const EXPECTED: Record<string, string[]> = {
  UserPromptSubmit: [
    'ledger-capture.py', 'inbox-drain.py', 'telegram-reply-directive.py',
    'provenance-gate.py', 'staleness-guard.py', 'channel-inbox-drain.py',
    'voice-reply-directive.py', 'telegram_progress.py', 'claude-usage.py',
  ],
  PostToolUse: [
    'ledger-outbound.py', 'tool-log-capture.py',
    'telegram_progress_reply_clear.py', 'skill-usage-capture.py',
  ],
  PreToolUse: [
    'outgoing-copy-gate.py', 'email-approval-gate.py',
    'channel-image-resize.sh', 'egress-gate.mjs',
  ],
  Stop: ['telegram-reply-guard.py', 'telegram_progress_clear.py'],
  SessionStart: ['ledger-replay.py', 'taskstate-replay.py', 'clear-replay.py'],
  SessionEnd: ['clear-capture.py'],
}

// LOCAL ADDITIONS -- this install only, deliberately NOT folded into EXPECTED above.
//
// WHY THEY ARE HERE: three gates that live in this fleet and not upstream. All
// three were put under version control on 2026-09-16; before that their wiring
// existed in exactly one working tree, and one of them
// (telegram-reply-context-patch's sibling class) exists precisely to survive
// plugin updates -- the kind of thing a checkout takes away silently.
//
// WHY A SEPARATE CONSTANT: EXPECTED above is upstream's literal, kept byte for
// byte. Folding our three names into it would make our lines and theirs conflict
// TOGETHER on every future upgrade, and a line that must be "merged carefully"
// every single round eventually gets merged carelessly. Kept apart, the
// resolution is mechanical: theirs replaces theirs, ours stays.
//
// WHAT THE ANCHOR STILL DOES: nothing is weakened. A DROPPED entry still fails
// the build -- measured both ways on 2026-09-16 by removing one upstream hook
// (egress-gate.mjs -> 2 failures) and one local hook (record-overwrite-gate.py ->
// 1 failure). The local three are therefore now PROTECTED by this anchor, which
// they were not before.
//
// AND IF YOU ADD A NEW LOCAL HOOK: this test will fail until you list it here.
// That is the gate working, not a regression. Adding a name is a reviewed
// decision about what runs in the main session -- the same bar EXPECTED sets.
const LOCAL_ADDITIONS: Record<string, string[]> = {
  UserPromptSubmit: ['telegram-ack.py'],
  PreToolUse: ['delegalt-iras-tiltas-kapu.py', 'record-overwrite-gate.py'],
}

// What THIS install must register: upstream's set plus the local additions.
const EXPECTED_HERE: Record<string, string[]> = Object.fromEntries(
  [...new Set([...Object.keys(EXPECTED), ...Object.keys(LOCAL_ADDITIONS)])].map((event) => [
    event,
    [...(EXPECTED[event] ?? []), ...(LOCAL_ADDITIONS[event] ?? [])],
  ]),
)

function commands(event: string): string[] {
  return (hooks[event] ?? []).flatMap((e) => e.hooks ?? []).map((h) => h.command ?? '')
}

function scriptNames(event: string): Set<string> {
  return new Set(
    commands(event)
      .map((c) => c.match(/scripts\/hooks\/([^/\s'"]+?\.(?:py|sh|mjs))/)?.[1] ?? '')
      .filter(Boolean),
  )
}

describe('tracked .claude/settings.json hook anchor (#1305)', () => {
  it('registers exactly the expected script set per event', () => {
    expect(Object.keys(hooks).sort()).toEqual(Object.keys(EXPECTED_HERE).sort())
    for (const [event, expected] of Object.entries(EXPECTED_HERE)) {
      expect([...scriptNames(event)].sort(), `event ${event}`).toEqual([...new Set(expected)].sort())
    }
  })

  it('every referenced script exists in scripts/hooks/', () => {
    for (const event of Object.keys(EXPECTED_HERE)) {
      for (const name of scriptNames(event)) {
        expect(existsSync(join(ROOT, 'scripts', 'hooks', name)), `missing scripts/hooks/${name}`).toBe(true)
      }
    }
  })

  it('every command is portable: $CLAUDE_PROJECT_DIR, no machine-local paths', () => {
    for (const event of Object.keys(hooks)) {
      for (const cmd of commands(event)) {
        expect(cmd, `event ${event}`).toContain('$CLAUDE_PROJECT_DIR')
        expect(cmd).not.toMatch(/\/(Users|home|opt|var)\//)
      }
    }
  })

  it('the WebFetch egress gate keeps its fail-closed preamble', () => {
    const webfetch = (hooks.PreToolUse ?? []).filter((e) => e.matcher === 'WebFetch')
    expect(webfetch).toHaveLength(1)
    const cmd = webfetch[0].hooks?.[0]?.command ?? ''
    // No node -> BLOCK (exit 2), never fail-open silence.
    expect(cmd).toMatch(/command -v node[^;]*\|\|\s*\{[^}]*exit 2/)
    expect(cmd).toContain('egress-gate.mjs')
  })
})
