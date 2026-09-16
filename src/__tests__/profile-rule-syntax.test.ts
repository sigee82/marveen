import { describe, expect, it } from 'vitest'
import { loadProfileTemplate, resolveProfilePlaceholders } from '../web/profiles.js'
import { PROJECT_ROOT } from '../config.js'

// TMPLPERM908: the permission-rule shapes below were MEASURED against Claude
// Code's engine on 2026-09-08 (strict launch, -p probes T1-T9):
//   - Read(/abs/path/**)  -> single leading '/' is project-relative, NEVER matches
//   - Read(//abs/path/**) -> matches (allow and deny)
//   - Read(~/path/**)     -> matches (allow and deny)
//   - Bash(/abs/**/x.sh:*) -> '**' has no glob meaning in Bash rules; only a
//                             literal command prefix matches
// These tests pin the normalization + template posture so a future edit cannot
// silently regress to the never-matching shapes.

const ctx = { HOME: '/Users/testuser', AGENT_DIR: '/Users/testuser/ClaudeClaw/agents/tester' }

describe('resolveProfilePlaceholders rule normalization', () => {
  it('rewrites a single-slash absolute Read rule to the // absolute form', () => {
    expect(resolveProfilePlaceholders('Read(${HOME}/.ssh/**)', ctx))
      .toBe('Read(//Users/testuser/.ssh/**)')
  })

  it('rewrites Edit and Write rules the same way', () => {
    expect(resolveProfilePlaceholders('Edit(${AGENT_DIR}/**)', ctx))
      .toBe('Edit(//Users/testuser/ClaudeClaw/agents/tester/**)')
    expect(resolveProfilePlaceholders('Write(/tmp/**)', ctx)).toBe('Write(//tmp/**)')
  })

  it('leaves already-absolute (//), home (~) and relative (**) rules untouched', () => {
    expect(resolveProfilePlaceholders('Read(//tmp/**)', ctx)).toBe('Read(//tmp/**)')
    expect(resolveProfilePlaceholders('Read(~/.claude/skills/**)', ctx)).toBe('Read(~/.claude/skills/**)')
    expect(resolveProfilePlaceholders('Read(**/.env)', ctx)).toBe('Read(**/.env)')
  })

  it('never touches Bash rules (command-prefix matching, not paths)', () => {
    expect(resolveProfilePlaceholders('Bash(sudo:*)', ctx)).toBe('Bash(sudo:*)')
    expect(resolveProfilePlaceholders('Bash(${PROJECT_ROOT}/scripts/notify.sh:*)', ctx))
      .toBe(`Bash(${PROJECT_ROOT}/scripts/notify.sh:*)`)
  })

  it('resolves ${PROJECT_ROOT}', () => {
    expect(resolveProfilePlaceholders('${PROJECT_ROOT}/scripts/x.sh', ctx))
      .toBe(`${PROJECT_ROOT}/scripts/x.sh`)
  })
})

describe('web-reading profile posture (TMPLPERM908)', () => {
  // Both profiles read web content (prompt-injection surface), and strict is
  // what makes the deny list enforceable: permissive launches with
  // --dangerously-skip-permissions. The owner nevertheless chose permissive,
  // twice -- 2026-09-07 (TG 14764, card PROFILSTRICT904) and again 2026-09-08
  // (TG 15115, card PROFILREGRESS908) after this test's predecessor reverted
  // the first, uncommitted flip. Measured reason: under strict the agent stops
  // on a permission dialog at EVERY tool call, including read-only ones, and no
  // one answers it in a non-interactive agent -- orsi filed two session-stuck
  // alarms in 25 minutes and did zero work. The deny list still carries the
  // real posture (SSH/AWS/.gnupg/.env reads, sudo, rm, and git push for researcher
  // only); it is simply advisory under permissive.
  //
  // `Bash(curl -X POST:*)` USED TO BE LISTED HERE and was removed on 2026-09-16.
  // It never fired and must not: the rule matches on a PREFIX, so any inserted
  // flag (`curl -s -X POST`) walks past it -- and the fleet's own documented
  // inter-agent send is exactly that command. A rule whose enforcement would
  // break the system's base operation is decorative, and the harm was not the
  // pass-through but the impression that POSTs were gated. What actually gates
  // outbound shell traffic is BASH_EGRESS_DENY in agent-scaffold.ts (https curl,
  // wget, nc, ncat, telnet); plain http, interpreter one-liners and a URL hidden
  // in a variable remain open BY STATED DECISION, see the comment above that
  // constant. Tightening the mode again is an OWNER decision,
  // not a template edit, and it must land with the agents' work rerouted first.
  for (const id of ['marketer', 'researcher']) {
    it(`${id} stays permissive (owner decision) and carries the measured capability allows`, () => {
      const p = loadProfileTemplate(id)
      expect(p.id).toBe(id) // guard against the default-profile fallback
      expect(p.permissionMode).toBe('permissive')
      expect(p.filesystem.allow).toContain('Read(${HOME}/.claude/skills/**)')
      expect(p.filesystem.allow).toContain('Bash(${PROJECT_ROOT}/scripts/notify.sh:*)')
      expect(p.filesystem.allow).toContain('Bash(${PROJECT_ROOT}/scripts/agent-post.sh:*)')
      expect(p.filesystem.deny).toContain('Read(${HOME}/.ssh/**)')
    })
  }

  it('no template carries a Bash rule with a ** glob (prefix matching cannot glob)', () => {
    for (const id of ['marketer', 'researcher', 'developer-junior', 'developer-senior', 'applier', 'sub-dev', 'default']) {
      const p = loadProfileTemplate(id)
      for (const rule of [...p.filesystem.allow, ...p.filesystem.deny]) {
        if (rule.startsWith('Bash(')) expect(rule).not.toContain('**')
      }
    }
  })
})
