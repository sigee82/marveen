#!/usr/bin/env node
// PreToolUse gate for outgoing Telegram messages: block tool-call markup that
// leaked into the message body.
//
// PROBLEM (2026-08-06, three occurrences in one morning): when the model's
// parameter block is closed with the wrong tag (`</text>` instead of
// `</parameter>`), two things happen and BOTH reach the owner:
//   1. a `files` parameter meant as an attachment ends up as raw XML inside the
//      message text -> the file is never sent, the owner sees
//      `<parameter name="files">["/Users/..."]`;
//   2. with no attachment, the stray closing tags land at the END of the sent
//      message -> the owner reads `...utolso mondat.</text>` `</invoke>`.
// In both cases the tool still returns `sent`, so nothing signals the mistake.
// The owner noticed twice and finally said: "ne legyen soha."
//
// FIX: deny the call before it goes out, and say exactly what to fix. This is a
// mechanical gate, not a note -- per skill `sajat-ismetlodo-hiba-kapuzasa`, a
// behavioural error that repeats needs a gate, not a fourth memory entry.
//
// Safe by construction: only DENY on a positive match, defer on everything else,
// and exit 0 on any parse/runtime error so a broken gate can never mute the
// channel.

import { readFileSync, realpathSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

// Telegram-facing tools whose payload reaches the owner verbatim.
const TELEGRAM_TOOLS = /telegram.*(reply|edit_message)/i

// Markup that must never appear in a message body. Deliberately narrow: these
// are tool-call delimiters, not text a human would send. Ordinary angle brackets
// ("<3", "a < b", HTML the owner asked for) do NOT match.
const LEAKED_MARKUP = [
  { re: /<\/(?:text|invoke|parameter|function_calls|antml:[a-z_]+)>/i, what: 'lezaro tag a szovegben' },
  { re: /<parameter\s+name\s*=/i, what: 'parameter-nyito tag a szovegben' },
  { re: /<(?:antml:)?(?:invoke|function_calls)\b/i, what: 'tool-hivas nyito tag a szovegben' },
]

// Fields whose content is sent to the user as-is.
const TEXT_FIELDS = ['text', 'caption', 'message']

// ---------------------------------------------------------------------------
// SECOND GATE: a significant NUMBER with no SOURCE anywhere in the message.
//
// PROBLEM (2026-08-08, three occurrences in one morning, all caught by a peer
// agent rather than by me): I passed on sentences that sounded finished but were
// never measured -- "this buyer NEVER reached the thank-you page" (born from a
// truncated log window I had myself refuted hours earlier), "so the ad-set field
// DOES reach the public page" (a favourable over-reading), and "the fix costs a
// learning reset" (an unmeasured cost claim that would have biased the owner's
// decision). All three were heading to the owner.
//
// Pixel's structural objection is why this gate exists: "I caught all three" is
// NOT a control, because a sub-agent only ever sees what is routed through it.
// A claim that goes from me straight to the owner passes no reviewer at all.
//
// The predicate is deliberately NARROW, because a noisy gate trains you to
// ignore it (see memory `kontroll-amit-sajat-muveletunk-mozgat`): fire only when
// the message carries a SIGNIFICANT figure (>=3 digits, money, percent, a
// multiplier) and carries NO source marker at all -- no time, no date, no
// "szerint"/"mérve"/"napló"/"log", nothing. An ordinary sourced report ("a
// CAPI-napló szerint 19 960 Ft") passes untouched; a bare "19 960 Ft" does not.
//
// It cannot catch a wrong conclusion drawn from a real measurement -- that stays
// a semantic problem, and the honest place for it is the brief sent to the
// measuring agent (state premises AS premises, so the reader knows what to
// attack). This gate only closes the narrower, mechanical hole.
// ---------------------------------------------------------------------------

// A figure worth sourcing. Small counts ("3 reakció", "2 nap") are exempt on
// purpose -- they are rarely the load-bearing number in a decision.
const SIGNIFICANT_FIGURE = [
  /\d[\d  .]{2,}\d\s*(?:Ft|EUR|USD|\$|€)/i, // 19 960 Ft, 1.443 Ft
  /\d+\s*(?:Ft|EUR|USD|\$|€)\s*\/\s*\w+/i, //       1000 Ft/nap
  /\d+[.,]?\d*\s*%/, //                             9,78%
  /\b\d+[.,]?\d*\s*x\b/i, //                        8x, 3,3x
  /\b\d{3,}\b/, //                                  any bare 3+ digit number
]

// Anything that anchors a figure to where it came from: a clock time, a date, a
// measurement verb, a named source.
//
// TWO BUGS MEASURED HERE (2026-08-08, Pixel read the code and ran the patterns
// on real Hungarian sentences) -- both made the gate silently inert:
//   1. `/\bm[eé]r(?:t|ve|...)\b/` matched "mert" (= because), one of the commonest
//      Hungarian conjunctions, so ANY explanatory sentence disabled the gate.
//      Fixed by requiring the accent that actually distinguishes the two words:
//      "mért" (measured) vs "mert" (because).
//   2. the time group had no closing `\b`, so "ma" matched MAJD, MARAD, MAXIMUM,
//      MAI and -- worst for this domain -- MARKETING.
// Consequence worth remembering: the original "seven real messages, zero false
// positives" result did NOT measure what it looked like. Several of those messages
// passed on "mert"/"ma..." accidents, not on being properly sourced. A green test
// whose green comes from a hole is a phantom control.
// SCOPE -- DO NOT REUSE THIS GATE ON INTER-AGENT TEXT.
// The accent binding below ("mért" measured vs "mert" because) is only safe
// because owner-facing Hungarian is required to carry accents (CLAUDE.md: never
// write Hungarian without accents). Inter-agent messages in this fleet are
// written WITHOUT accents, so every accent-less "mert" (= measured) would stop
// counting as a source and the gate would fire more or less at random. The error
// direction is the safe one (deny, not pass), but a noisy gate trains you to
// ignore it -- which defeats the whole point. Owner channels only.
// (Boundary raised by Pixel, 2026-08-08: a condition that is true today and can
// quietly stop being true is exactly the kind that needs writing down.)
const SOURCE_MARKER = [
  /\b\d{1,2}:\d{2}\b/, //                           09:20
  /\b\d{4}-\d{2}-\d{2}\b/, //                       2026-08-08
  /\b\d{1,2}-[a-záéíóöőúüű]+\b/i, //                08-07, 7-én
  /\bmért\b/, //                                    "mért" -- NOT "mert" (because)
  /\bmér(?:ve|tem|ted|és|ési)\b/i,
  /\bnapl[oó]/i,
  /\blog\b/i,
  /\bszerint\b/i,
  /\bforr[aá]s/i,
  /\bell[eő]n[oő]riz/i,
  /\beml[eé]k/i,
  /\b[oó]ta\b/i,
  /\b\d{1,2}-kor\b/i,
  // Adding the closing \b (fix 2) made these suffixed forms stop matching, which
  // is how Hungarian actually writes them: "tegnapi kép", "mai szám", "reggeli
  // vásárlás". Enumerated rather than left open-ended, so "MAJD"/"MARKETING" stay
  // out -- an open suffix is what made the pattern inert in the first place.
  /\b(?:ma|mai|tegnap|tegnapi|reggel|reggeli|d[eé]lut[aá]ni?|est[ei]|hajnal|hajnali)\b/i,
]

// How far a source marker may sit from the figure it anchors. Message-level
// checking was the third defect Pixel found: a single timestamp in the opening
// line exempted every other number in an eight-point report, so the gate never
// required a figure and its source to have anything to do with each other.
// A window is the compromise -- strict enough that a bare figure buried in a long
// sourced message still fires, loose enough that a source in the neighbouring
// sentence still counts (measured against the real messages in the test file).
const SOURCE_WINDOW = 220

// A URL SZAMAI CIMEK, NEM ALLITASOK -- ES A KAPU 2026-09-14-ig MINDET LELOTTE.
// Mert eset: egy OAuth authorize-link kikuldese NEGYSZER bukott el egymas utan. A
// `redirect_uri=http%3A%2F%2F127.0.0.1%3A3001%2F...` reszben a `0.1%` illeszkedett a
// szazalek-mintara, a `3001` es a `256` pedig a "harom+ jegyu csupasz szam" mintara.
// Egyik sem allitas a vilagrol: egy visszahivasi cim es egy PKCE-parameter.
// MIERT NEM ELEG "megkerulni": a kapu celja az, hogy a MERES NELKULI SZAM ne menjen ki.
// Egy kapu viszont, ami rendszeresen jo tartalmat utasit el, a felulbiralo reflexet
// tanitja meg -- es akkor a VALODI eset is at fog csuszni. A hamis pozitivot tehat
// javitani kell, nem kikerulni. (Aznap epp ez tortent: a linket fajlkent, majd
// csonkitva kuldtem ki, mert a szoveges ut zarva volt.)
// A SZUKITES SZANDEKOSAN SZUK: csak a URL-en BELULI illeszkedest hagyjuk ki. Egy
// mondatban allo szazalek vagy penzosszeg valtozatlanul tuzel.
const URL_SPAN = /\bhttps?:\/\/\S+/gi

function urlSpans(text) {
  const spans = []
  let m
  const re = new RegExp(URL_SPAN.source, URL_SPAN.flags)
  while ((m = re.exec(text)) !== null) spans.push([m.index, m.index + m[0].length])
  return spans
}

function insideUrl(spans, start, end) {
  return spans.some(([a, b]) => start >= a && end <= b)
}

function unsourcedFigure(text) {
  const spans = urlSpans(text)
  for (const re of SIGNIFICANT_FIGURE) {
    const flags = re.flags.includes('g') ? re.flags : re.flags + 'g'
    const global = new RegExp(re.source, flags)
    let m
    while ((m = global.exec(text)) !== null) {
      if (insideUrl(spans, m.index, m.index + m[0].length)) continue
      const from = Math.max(0, m.index - SOURCE_WINDOW)
      const to = Math.min(text.length, m.index + m[0].length + SOURCE_WINDOW)
      const near = text.slice(from, to)
      if (!SOURCE_MARKER.some((s) => s.test(near))) return m[0].trim()
      if (m[0].length === 0) break // never loop forever on a zero-width match
    }
  }
  return null
}

// Pure decision. Returns { decision: 'deny'|'defer', reason? }.
export function gateDecision(toolName, toolInput) {
  if (!TELEGRAM_TOOLS.test(String(toolName ?? ''))) return { decision: 'defer' }
  if (!toolInput || typeof toolInput !== 'object') return { decision: 'defer' }

  for (const field of TEXT_FIELDS) {
    const value = toolInput[field]
    if (typeof value !== 'string' || !value) continue
    for (const { re, what } of LEAKED_MARKUP) {
      const m = value.match(re)
      if (m) return { decision: 'deny', reason: denyMessage(field, what, m[0]) }
    }
  }
  for (const field of TEXT_FIELDS) {
    const value = toolInput[field]
    if (typeof value !== 'string' || !value) continue
    const figure = unsourcedFigure(value)
    if (figure) return { decision: 'deny', reason: figureMessage(field, figure) }
  }
  // A HOSSZ-KAPU UTOLSONAK FUT: eloszor a tartalmi hibak (szivargott jelolo,
  // forras nelkuli szam), mert azok javitasa amugy is atirja a szoveget.
  for (const field of TEXT_FIELDS) {
    const value = toolInput[field]
    if (typeof value !== 'string' || !value) continue
    const hossz = tulHosszu(value)
    if (hossz) return { decision: 'deny', reason: hosszMessage(field, hossz) }
  }
  return { decision: 'defer' }
}

function figureMessage(field, figure) {
  return (
    `KAPU: a Telegram-uzenet "${field}" mezojeben szam all ("${figure}") FORRAS NELKUL -- ` +
    'nincs benne idopont, datum, "szerint", "merve", "naplo", "log" vagy emlek-hivatkozas. ' +
    'Az uzenet NEM ment ki. OK (2026-08-08, harom eset egy delelott): a meres nelkuli szam ' +
    'ugyanolyan magabiztosan hangzik, mint a mert, es a gazda a szamot viszi tovabb, nem a fenntartast. ' +
    'JAVITAS ket lehetoseg: (1) ird a szam melle, MIVEL es MIKOR merted (pl. "a CAPI-naplo szerint", ' +
    '"08:45-kor merve"); (2) ha nem merted, MERD MEG, vagy kerd attol az agenstol, akinek eszkoze van ra. ' +
    'Ha a szam a gazda sajat adata (o mondta, vagy egy tole jott szamot ismetelsz vissza), ' +
    'akkor is nevezd meg a forrast egy szoval ("ahogy irtad").'
  )
}

// --- HOSSZ-KAPU ---------------------------------------------------------------
// A CLAUDE.md szerint a Telegram-valasz alapertelmezese 2-5 sor. 2026-08-27-en
// MEGMERTEM a sajat aznapi uzeneteimet: 7-14 sor, 400-1500 karakter, majdnem
// mindegyik. Zsolt aznap HAROMSZOR kifogasolta ("nagyon sokat irsz", "megint
// hadovalsz ossze-vissza", "ne faszom kormondatokat irkalj tok feleslegesen").
// A szabaly a CLAUDE.md-ben all, tudom is -- es megis megszegem. Tehat NEM
// tudasbeli a hiba, hanem viselkedesi, es a valasz nem ujabb feljegyzes, hanem
// kapu (lasd `sajat-ismetlodo-hiba-kapuzasa`).
//
// NEM HARD DENY: van, amikor a hosszu uzenet a helyes (mert szamok atadasa,
// dontesi lista). De akkor is LEGYEN DONTES, ne sodrodas -- ezert a kapu
// megall, es a `HOSSZU:` prefixszel lehet atengedni. Egy tudatos szo aran.
const MAX_SOR = 6
const MAX_KARAKTER = 700
// A ket kapu OSSZEUTKOZOTT (2026-08-27, eles eset): ez a prefix ekezet nelkuli volt,
// az outgoing-copy-gate helyesirasi szabalya viszont a "hosszu" szot ekezettel koveteli.
// Igy egy jogos, hosszu uzenet NEM tudott kimenni: a HOSSZU: alakot a masik kapu vagta el,
// az ekezetes HOSSZU:-t meg ez nem ismerte fel. Mindketto elfogadva.
const HOSSZ_MENTESSEG = /^\s*HOSSZ[UÚ]:/i

function tulHosszu(text) {
  if (HOSSZ_MENTESSEG.test(text)) return null
  const sorok = text.split('\n').filter((s) => s.trim() !== '').length
  const karakter = text.length
  if (sorok <= MAX_SOR && karakter <= MAX_KARAKTER) return null
  return { sorok, karakter }
}

function hosszMessage(field, m) {
  return (
    `KAPU: a Telegram-uzenet "${field}" mezoje ${m.sorok} nem-ures sor / ${m.karakter} karakter ` +
    `(a hatar ${MAX_SOR} sor / ${MAX_KARAKTER} karakter). Az uzenet NEM ment ki. ` +
    'OK: a CLAUDE.md szerint az alapertelmezes 2-5 sor -- a DONTES es a KOVETKEZO LEPES, semmi mas. ' +
    '2026-08-27-en a sajat aznapi uzeneteim 7-14 sorosak voltak, es a gazda HAROMSZOR kifogasolta. ' +
    'JAVITAS: vagd ki, amit nem kerdezett -- miert dontottel ugy, mit es hogyan ellenoriztel, ' +
    'mit csinalt jol egy sub-agens, elvetett alternativak. Azok a transzkriptbe es a memoriaba valok. ' +
    'HA A HOSSZ TENYLEG INDOKOLT (mert szamok atadasa, dontesi lista), akkor a szoveg elejere ' +
    'ird oda: HOSSZU: -- ettol atmegy, es a prefixet a kuldes elott vedd ki. Egy tudatos dontes ara.'
  )
}

function denyMessage(field, what, sample) {
  return (
    `KAPU: tool-hivas jelolo szivargott a Telegram-uzenet "${field}" mezojebe (${what}: ${sample}). ` +
    'Az uzenet NEM ment ki -- a gazda ezt nyers szovegkent latna. ' +
    'OK: a parametert `</parameter>` zarja, NEM `</text>`; a nyito tag NEVE nem a zaro tag neve. ' +
    'JAVITAS: ird ujra a hivast tisztan. Ha fajlt kuldesz, a `files` KULON parameter legyen, ' +
    'es a valasz `sent 2 parts` legyen -- a puszta `sent` azt jelenti, hogy a csatolmany NEM ment el. ' +
    'Hosszabb uzenetnel csuszik el a leggyakrabban: rovid kiserooszoveg + kulon uzenet a magyarazatnak.'
  )
}

function emitDeny(reason) {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'deny',
        permissionDecisionReason: reason,
      },
    }),
  )
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
  try {
    const { decision, reason } = gateDecision(payload?.tool_name, payload?.tool_input)
    if (decision === 'deny') emitDeny(reason)
  } catch {
    process.exit(0) // a broken gate must never block the channel
  }
  process.exit(0) // defer
}
