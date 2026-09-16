import { describe, it, expect } from 'vitest'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

// The secret-read branch of scripts/hooks/bash-safety-gate.mjs had NO test at all
// (measured 2026-09-16) -- a security hook whose behaviour nobody would notice
// changing. These cases pin what it does AND, deliberately, what it does not.
//
// THE GATE IS ASKED, NOT EXERCISED. It is a pure function of the command text, so
// every case below is a verdict on a string; no file is opened and nothing runs.
// That matters here specifically: probing a real ~/.ssh file to see whether the
// gate stops you means the content crossed the tool boundary if it did not.
//
// Resolved relative to this file, not to an absolute install path: a hook test
// pointing at /Users/... measures the deployed tree instead of the one it ships
// with.
const GATE = fileURLToPath(new URL('../../scripts/hooks/bash-safety-gate.mjs', import.meta.url))

function verdict(command: string): { denied: boolean; secretBranch: boolean } {
  let out = ''
  try {
    out = execFileSync('node', [GATE], {
      input: JSON.stringify({ tool_name: 'Bash', tool_input: { command } }),
      encoding: 'utf8',
    })
  } catch (e) {
    out = (e as { stdout?: string }).stdout ?? ''
  }
  if (!out.trim()) return { denied: false, secretBranch: false }
  const j = JSON.parse(out) as {
    hookSpecificOutput?: { permissionDecision?: string; permissionDecisionReason?: string }
  }
  const denied = j.hookSpecificOutput?.permissionDecision === 'deny'
  const reason = j.hookSpecificOutput?.permissionDecisionReason ?? ''
  return { denied, secretBranch: denied && reason.startsWith('Titok-anyag') }
}

const SECRET = '/Users/macmini/.ssh/config'

describe('bash-safety-gate: secret reads', () => {
  // The enumerated readers. A deny here must come from the SECRET branch -- another
  // rule happening to catch the same string would make this test pass for the wrong
  // reason, which is how `dd if=...` looked like a win until the reason was read.
  const READERS = [
    'cat', 'less', 'more', 'head', 'tail', 'bat', 'nl', 'xxd', 'od', 'strings',
    'cp', 'scp', 'rsync', 'sed', 'awk', 'grep', 'base64', 'cut', 'tr', 'perl',
  ]

  for (const cmd of READERS) {
    it(`${cmd} on a secret path is refused by the secret rule`, () => {
      const v = verdict(`${cmd} ${SECRET}`)
      expect(v.denied, `${cmd} passed`).toBe(true)
      expect(v.secretBranch, `${cmd} denied, but by a different rule`).toBe(true)
    })
  }

  it('covers the other secret roots, not just .ssh', () => {
    expect(verdict('grep SECRET /Users/macmini/.aws/credentials').secretBranch).toBe(true)
    expect(verdict('sed -n 1p /Users/macmini/marveen/.env').secretBranch).toBe(true)
    expect(verdict('cat /Users/macmini/.gnupg/secring.gpg').secretBranch).toBe(true)
  })

  // The other direction. Without these the rule could be tightened into refusing
  // ordinary work and every assertion above would still pass.
  it('leaves ordinary reads alone', () => {
    for (const cmd of [
      'cat /Users/macmini/marveen/README.md',
      'head -5 /Users/macmini/marveen/package.json',
      'sed -n 1,5p /Users/macmini/marveen/README.md',
      'grep -n version /Users/macmini/marveen/package.json',
      'awk {print $1} /Users/macmini/marveen/package.json',
      'cut -d, -f1 /Users/macmini/marveen/store/x.csv',
      'tr a b < /Users/macmini/marveen/README.md',
      'perl -pe s/a/b/ /Users/macmini/marveen/README.md',
    ]) {
      expect(verdict(cmd).denied, cmd).toBe(false)
    }
  })

  // >>> THE GAP, PINNED ON PURPOSE. <<<
  //
  // These four pass today. The rule is a speed bump against a casual or injected
  // `cat ~/.ssh/id_rsa`, not containment, and an interpreter one-liner cannot be
  // enumerated away. Measured 2026-09-16: widening the reader list took the
  // trivially available alternatives from 11 to these 4.
  //
  // IF YOU CLOSE ONE, THIS TEST FAILS -- that is the point. Update the count in the
  // gate's comment in the same change, or the rule slowly looks complete while the
  // class stays open.
  it('the known gap is still exactly these four (fails when it changes, deliberately)', () => {
    const open = [
      `python3 -c print(open('${SECRET}').read())`,
      `node -e console.log(require('fs').readFileSync('${SECRET}','utf8'))`,
      'tar cf - /Users/macmini/.ssh/',
      'ditto /Users/macmini/.ssh /tmp/x',
    ]
    for (const cmd of open) expect(verdict(cmd).denied, cmd).toBe(false)
  })

  // Known false positive, kept because the safe alternative is worse: `.env.example`
  // and `.env.production` are the same shape, so freeing the template frees a real
  // secret file too.
  it('refuses env TEMPLATES as well -- a known, accepted false positive', () => {
    expect(verdict('grep -n PORT /Users/macmini/marveen/.env.example').secretBranch).toBe(true)
  })
})
