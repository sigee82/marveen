// Run scripts/self-pace-gate.mjs against a fixture file; one line per case.
//
// See scripts/selfpace-gate-fixtures.txt for what this exists to preserve: a
// negative finding (2026-09-16) that the gate is NOT the cause of a block whose
// command text merely names a scheduling command.
//
// NOTE ON WRITING FIXTURES: the fixture file has to be created with a file-writing
// tool, not a shell heredoc -- the gate blocks the heredoc itself, because the test
// DATA contains the command it recognises. That is not a bug in the gate; it is why
// a report about it is awkward to produce from a shell. The right move there is the
// other route (write the file), never relaxing the gate.
//
// Run: node scripts/selfpace-gate-measure.mjs scripts/selfpace-gate-fixtures.txt
// Exit 0 if every case matched its class's expectation, 1 otherwise.
import { readFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
// Relative to this file, not an absolute install path: a hook test that points at
// /Users/... measures the deployed tree instead of the one it ships with.
const GATE = process.argv[3] ?? join(HERE, 'self-pace-gate.mjs')

const WANT = {
  VALODI_HIVAS: 'deny',
  JELENTES: 'allow',
  INERT_IDEZETT: 'allow',
  INERT_HEREDOC: 'allow',
  OLVASAS: 'allow',
}

const lines = readFileSync(process.argv[2], 'utf8')
  .split('\n')
  .map((l) => l.trim())
  .filter((l) => l && !l.startsWith('#'))

let mismatches = 0
for (const line of lines) {
  const [cls, ...rest] = line.split('|')
  const cmd = rest.join('|').replace(/\\n/g, '\n')
  const want = WANT[cls]
  if (!want) {
    console.log(`!! ISMERETLEN OSZTALY: ${cls}`)
    mismatches++
    continue
  }
  let out = ''
  try {
    out = execFileSync('node', [GATE], {
      input: JSON.stringify({ tool_name: 'Bash', tool_input: { command: cmd } }),
      encoding: 'utf8',
    })
  } catch (e) {
    out = e.stdout ?? ''
  }
  let decision = 'allow'
  try {
    if (out.trim()) decision = JSON.parse(out).hookSpecificOutput?.permissionDecision ?? 'allow'
  } catch {
    decision = 'allow'
  }
  const ok = decision === want
  if (!ok) mismatches++
  console.log(`${ok ? '   ' : '!! '}${cls.padEnd(14)} ${decision.padEnd(6)} (vart: ${want})  ${cmd.replace(/\n/g, ' \\n ').slice(0, 64)}`)
}

console.log(`\nELTERES A VARTTOL: ${mismatches} / ${lines.length}`)
process.exit(mismatches === 0 ? 0 : 1)
