// Which fields PATCH/PUT /api/memories/:id will actually act on.
//
// Same shape and the same reason as agent-put-fields.ts: split out of the route
// handler so the rule is testable without an HTTP context, because its failure
// mode is silence.
//
// Background (Atlas measured it, 2026-09-16): the handler destructured the five
// fields it understood and ignored everything else. A body of {"probe":1} was
// answered 200 {"ok":true} -- and the row was byte-identical afterwards (1450
// chars before and after). A real {"content":"..."} on the same id worked
// (1450 -> 1894). The two outcomes are INDISTINGUISHABLE from the caller's side,
// so a misspelled field name reads as a completed edit. An empty {} does the
// same thing: content is backfilled from the existing row and written back
// unchanged, which is a successful write that applies nothing anyone asked for.
//
// The readback that would have caught it did not exist either: there was no
// GET /api/memories/:id, so confirming an edit meant running a search. Both
// halves are fixed together, because a silent write is only dangerous while the
// cheap way to check it is missing.

export const MEMORY_UPDATE_FIELDS = [
  'content', 'category', 'agent_id', 'keywords',
  // Deprecated alias for `category`, still accepted by the route (it logs a
  // deprecation warning). Listed so an old caller is not broken by this check.
  'tier',
  // MEMVERSION930 (upstream v1.42.0): the server puts this text in front of the
  // current content. It IS an edit, so it counts as substantive -- without it
  // here a prepend-only body was refused as "unknown field" by this check.
  'prepend',
] as const

// Keys that are RECOGNISED but do not by themselves constitute an edit.
//
// MEMIRASNYOM915 (upstream, merged 2026-09-23) added `updated_by`: the writer's
// self-reported identity, stored as a write-trace. It has to pass the
// unknown-key rule, or the trace field would 400 -- but it must NOT satisfy the
// "something is actually being updated" rule, because a body carrying only
// `updated_by` is exactly the no-op write this module exists to reject: content
// would be backfilled from the existing row and written back unchanged, and the
// caller would read ok:true.
//
// Two lists, because the two questions are different: "do I recognise this
// key?" and "is anything being changed?". One list answered both, and that is
// why adding a field to it would have quietly reopened the hole.
// MEMVERSION930 added `if_version`: a precondition (409 when the row changed
// since the caller read it), not a change. Recognised, never substantive -- a
// body carrying only `if_version` would be the same no-op write.
export const MEMORY_UPDATE_TRACE_FIELDS = ['updated_by', 'if_version'] as const

export type MemoryUpdateFieldCheck =
  | { ok: true }
  | { ok: false; message: string }

// Rejects the UNKNOWN rather than allow-listing the known at the call site, and
// additionally requires that at least one known field is PRESENT. The second
// rule is what catches {} -- a body with no unknown keys at all, which the
// key-rejection rule alone waves through into a no-op write.
//
// Deliberately checks KEYS, not values: the route still coerces and validates
// the values themselves (category against MEMORY_CATEGORIES, content against
// the security filter). A misspelled key is what was silent; a bad value was
// already loud.
export function checkMemoryUpdateFields(body: unknown): MemoryUpdateFieldCheck {
  if (body === null || typeof body !== 'object' || Array.isArray(body)) {
    return { ok: false, message: 'Request body must be a JSON object.' }
  }
  // `known` = substantive (what counts as an edit); `recognised` = substantive
  // plus trace (what the endpoint will not reject).
  const known = new Set<string>(MEMORY_UPDATE_FIELDS)
  const recognised = new Set<string>([
    ...MEMORY_UPDATE_FIELDS,
    ...MEMORY_UPDATE_TRACE_FIELDS,
  ])
  const keys = Object.keys(body as Record<string, unknown>)
  const rejected = keys.filter(k => !recognised.has(k))
  if (rejected.length) {
    return {
      ok: false,
      message:
        `Unknown field(s) for this endpoint: ${rejected.join(', ')}. ` +
        `Accepted: ${[...recognised].join(', ')}.`,
    }
  }
  if (!keys.some(k => known.has(k))) {
    return {
      ok: false,
      message:
        `Nothing to update: the body carries none of ${MEMORY_UPDATE_FIELDS.join(', ')}. ` +
        `An empty update would answer ok:true without changing anything.`,
    }
  }
  return { ok: true }
}
