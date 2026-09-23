import { describe, it, expect } from 'vitest'
import { withContextSuffix } from '../web/active-model.js'

// MAINMODEL923: the API never echoes the [1m] context suffix into the
// transcript, so a 1M session read raw looks like a 200k one.
describe('withContextSuffix', () => {
  it('re-attaches the suffix when the base model matches', () => {
    expect(withContextSuffix('claude-opus-5-5', 'claude-opus-5-5[1m]')).toBe('claude-opus-5-5[1m]')
  })
  it('keeps a real drift visible (different base model)', () => {
    expect(withContextSuffix('claude-opus-5', 'claude-opus-5-5[1m]')).toBe('claude-opus-5')
  })
  it('leaves suffix-less configs untouched', () => {
    expect(withContextSuffix('claude-opus-5-5', 'claude-opus-5-5')).toBe('claude-opus-5-5')
  })
  it('passes null through (no transcript line yet)', () => {
    expect(withContextSuffix(null, 'claude-opus-5-5[1m]')).toBeNull()
  })
})
