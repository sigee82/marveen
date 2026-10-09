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
//
// Both channel providers' progress hooks are listed unconditionally. That is
// deliberate: each one is provider-scoped internally and no-ops on the other
// provider's turns, so the cost of the idle set is a process spawn. Only the
// watchdog DAEMON -- which polls on a timer whether or not a turn is in
// flight -- is gated to the active CHANNEL_PROVIDER, by the two
// install-*-progress-hook.sh scripts.
const EXPECTED: Record<string, string[]> = {
  UserPromptSubmit: [
    'ledger-capture.py', 'inbox-drain.py', 'telegram-reply-directive.py',
    'provenance-gate.py', 'staleness-guard.py', 'memory-lookup-nudge.py', 'channel-inbox-drain.py',
    'voice-reply-directive.py', 'telegram_progress.py', 'slack_progress.py',
    'marveen-commands.py',
  ],
  PostToolUse: [
    'ledger-outbound.py', 'tool-log-capture.py',
    'telegram_progress_reply_clear.py', 'slack_progress_reply_clear.py',
    'skill-usage-capture.py', 'memory-frontmatter-bash-gate.py',
    // The persona guard watches the main agent's own CLAUDE.md/SOUL.md and
    // every agents/*/ pair, and it must fire on EVERY tool call: the first
    // version filtered on the Write/Edit file_path and a python3 heredoc
    // walked straight past it. PostToolUse is the event that cannot be
    // dodged by choosing a different tool.
    'persona-change-notify.py',
  ],
  // A failed tool call fires PostToolUseFailure, never PostToolUse
  // (TOOLLOGVAKSIKER921): without this entry tool_call_log cannot hold a 0.
  // KAPUEGYUT918: a failed Bash call can still have written a memory file.
  PostToolUseFailure: ['tool-log-capture.py', 'memory-frontmatter-bash-gate.py'],
  PreToolUse: [
    'outgoing-copy-gate.py', 'email-approval-gate.py',
    'channel-image-resize.sh', 'egress-gate.mjs', 'memory-frontmatter-gate.py',
    'memory-frontmatter-bash-gate.py',
  ],
  Stop: ['marveen-commands.py', 'telegram-reply-guard.py', 'telegram_progress_clear.py', 'slack_progress_clear.py'],
  SessionStart: ['ledger-replay.py', 'taskstate-replay.py', 'clear-replay.py', 'marveen-commands.py'],
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
// OWNER DECISION, 2026-09-23: the two "the agent noticed you" niceties are OFF.
// Zsolt had them turned off the day before and they came back when this merge
// restored telegram_progress.py (its absence looked like collateral damage,
// because nine agents still carried it) and wired telegram-ack.py for the first
// time. His words: the auto-like on his messages and the "working on it" reply
// are not wanted. Both are now absent from every surface, this file included.
//
// telegram_progress.py sits in upstream's EXPECTED above, which is kept byte for
// byte, so it is subtracted here rather than edited out of that list -- the
// divergence stays visible and survives the next upgrade instead of being
// silently re-merged.
const LOCAL_REMOVALS: Record<string, string[]> = {
  UserPromptSubmit: ['telegram_progress.py'],
}

const LOCAL_ADDITIONS: Record<string, string[]> = {
  // MERGE 2026-09-23: three more local PreToolUse gates were wired in
  // .claude/settings.json but never listed here, so the anchor did not protect
  // them -- and two of the three (interagent-homoglifa-kapu.py,
  // cso-exit-kod-kapu.py) were not even under version control, which is why a
  // fresh checkout wired two hooks whose files did not exist. Both are tracked
  // as of this merge. Listing them is the second half of that fix: a name here
  // is what makes a silent DROP fail the build.
  PreToolUse: [
    'delegalt-iras-tiltas-kapu.py', 'record-overwrite-gate.py',
    'interagent-homoglifa-kapu.py', 'idobelyeg-gate.py', 'cso-exit-kod-kapu.py',
    // The five governance gates + the Telegram text gate. Upstream ships all of
    // them UNWIRED, and on this install they were registered only in the ten
    // agents' own (gitignored) settings files -- so they existed on exactly one
    // machine, were absent for nova and nessa, and no fresh install reproduced
    // them. They are now on the seeding template AND here, so the main agent is
    // covered too. Measured 2026-09-23: mcp-permission-gate.mjs, the ads write
    // gate, was wired for 8 agents and for the main session NOWHERE.
    'bash-safety-gate.mjs', 'read-safety-gate.mjs', 'edit-safety-gate.mjs',
    'orchestration-safety-gate.mjs', 'mcp-permission-gate.mjs',
    'telegram-text-gate.mjs',
    // v1.42.0 merge: wired on 2026-09-26 (ssh-burst) and 2026-10-09 (launchd
    // PATH) in the working tree, committed with this merge.
    'ssh-burst-gate.py', 'launchagent-path-kapu.py',
  ],
  // v1.42.0 merge: the secret-in-output gate, wired 2026-09-28 with a
  // machine-local absolute path; now $CLAUDE_PROJECT_DIR like the rest.
  PostToolUse: ['titok-kimenet-kapu.py'],
  SessionStart: ['memoria-index-meret-kapu.py'],
}

// What THIS install must register: upstream's set plus the local additions.
const EXPECTED_HERE: Record<string, string[]> = Object.fromEntries(
  [...new Set([...Object.keys(EXPECTED), ...Object.keys(LOCAL_ADDITIONS)])].map((event) => [
    event,
    [...(EXPECTED[event] ?? []), ...(LOCAL_ADDITIONS[event] ?? [])]
      .filter((name) => !(LOCAL_REMOVALS[event] ?? []).includes(name)),
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
