import { describe, it, expect } from 'vitest'
import { checkMemoryUpdateFields, MEMORY_UPDATE_FIELDS } from '../web/memory-update-fields.js'

describe('checkMemoryUpdateFields', () => {
  // The measured case: this exact body was answered 200 {ok:true} and changed
  // nothing (Atlas, 2026-09-16).
  it('rejects a body whose only field is unknown', () => {
    const r = checkMemoryUpdateFields({ probe: 1 })
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.message).toContain('probe')
  })

  // The half the key-rejection rule alone does NOT catch: no unknown keys, and
  // still a no-op write.
  it('rejects an empty body', () => {
    const r = checkMemoryUpdateFields({})
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.message).toContain('Nothing to update')
  })

  it('rejects a misspelled field even next to a valid one', () => {
    const r = checkMemoryUpdateFields({ content: 'x', categry: 'cold' })
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.message).toContain('categry')
  })

  it('rejects a non-object body', () => {
    expect(checkMemoryUpdateFields(null).ok).toBe(false)
    expect(checkMemoryUpdateFields('content').ok).toBe(false)
    expect(checkMemoryUpdateFields([{ content: 'x' }]).ok).toBe(false)
  })

  // Positive controls: every accepted field, alone, must pass -- otherwise the
  // check would be "green" by refusing everything.
  it('accepts each known field on its own', () => {
    for (const f of MEMORY_UPDATE_FIELDS) {
      expect(checkMemoryUpdateFields({ [f]: 'x' }), `field ${f}`).toEqual({ ok: true })
    }
  })

  it('accepts the category-only tier move the Dream Engine makes', () => {
    expect(checkMemoryUpdateFields({ category: 'cold' })).toEqual({ ok: true })
  })

  it('accepts a full update', () => {
    expect(checkMemoryUpdateFields({
      content: 'x', category: 'warm', agent_id: 'nova', keywords: 'a, b',
    })).toEqual({ ok: true })
  })
})
