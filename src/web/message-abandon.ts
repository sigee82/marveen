// A message whose target session has been ABSENT for this whole window is
// marked failed, so it stops clogging the pending queue and we stop re-scanning
// it forever. Matches the scheduled-task retry window so a long turn that ate
// one also eats the other.
//
// ABSENT, NOT BUSY -- and this comment used to say otherwise, which is the only
// reason it is spelled out here. It read "target session never exists / stays
// busy", describing the behaviour from BEFORE shouldAbandon() was fixed (see its
// docstring in message-router.ts: the old inline code abandoned messages to an alive-but-busy session
// at the 1h mark, and two reports were lost that way). The code moved on; this
// comment did not, and it sits exactly where someone looking up the constant
// will read it. On 2026-09-22 it cost a round: I reported to the fleet that a
// one-hour uninterrupted tool chain makes inbound messages disappear. It does
// not -- shouldAbandon() requires !sessionExists, so a busy live session only
// ever DELAYS delivery. A stale comment next to a live constant is worse than
// no comment: it answers the question the reader actually asks.
//
// Lives in its own module so the POST /api/messages route can quote the same
// number in its "queued" warning without importing the router.
export const MESSAGE_ABANDON_WINDOW_MS = 60 * 60 * 1000
