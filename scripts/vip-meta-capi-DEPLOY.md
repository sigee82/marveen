# VIP CAPI Purchase fix - deploy note

> **SUPERSEDED for the renewal guard, 2026-08-15.** 4.0's "first purchase only" guard was measured
> wrong (it skipped nothing in 34 sends) and is replaced in 5.0 - see `vip-meta-capi-v5-DEPLOY.md`
> and `vip-meta-capi-v5-PLAN.md`. Everything else in this note - the event id bridge and its JS
> half, the dev leak, the second-sender history - still stands and is not restated there.

Bit, 2026-08-07. Card 9176b492. Prod deploy is Nova's (Bit has no SSH to vip.21napalatt.hu).

> **A `7b63787f...` HASH ELAVULT, es a `scripts/vip-meta-capi-v4.php` MAR NEM a kihelyezett
> forras (Bit, 2026-09-21).** A `prod` agon allo
> `wp-content/mu-plugins/vip-meta-capi.php` 26279 byte, md5 `5368b618b6e060c9402c6bf57085da5f`
> (`gh api .../contents/...?ref=prod` -bol kiolvasva). A repo-beli v4-hez kepest PONTOSAN harom
> hunk a kulonbseg, mind a 09-15-i fbc-jelzes: a `vip_capi_fbc_note()` es a
> `vip_capi_fbc_from_custom2()` fuggveny, plusz a ket naplosor (`ag=sent` es `ag=skipped-renewal`)
> kiegeszitese a `kor=` mezovel. Minden mas byte-ra azonos.
>
> **MIERT ALL EZ ITT ES NEM EGY EMLEKBEN:** ma egy `kor`-kerdesre a `scripts/vip-meta-capi-v4.php`
> -bol indultam, es ott NINCS `kor` -- abbol az kovetkezett volna, hogy a mezo nem is letezik a
> connectorban. A kihelyezett fajl a `prod` ag, nem ez a mappa.
>
> Ez a hash a PROD AGON merve van, nem a futo fajlon. A ketto egyezeset egy `md5sum` mondja meg
> a szerveren -- az SSH Novae.

## PENDING: v4 + the shared event_id (not deployed as of 2026-08-07 13:00)

v3 is live and verified. v4 is the next step and is **deliberately not shipped yet** - its JS
half goes into the live subscription pages, which deserves its own focused window.

| File | Target | md5 |
|------|--------|-----|
| `vip-meta-capi-v4.php` | `wp-content/mu-plugins/vip-meta-capi.php` | `7b63787fd89238ae8110e3638003ea95` |
| `vip-elofizetes-eventid-bridge.js` | the Elementor HTML widget on the two subscription pages | `42fde4a613a72d4c6b155d0a47a85c4a` |

**Where the JS goes.** There is no file to point at - the embed script lives in
`_elementor_data` post meta on `/eves-elofizetes/` and `/havi-elofizetes/`. In that widget,
find the literal `fbp:` - that is where the custom2 value is built - and replace that one
expression with `vipBuildCustom2()`. Paste the bridge snippet into the same widget *above*
the existing script.

Three things that otherwise make the deploy look like it failed:

1. **Keep the URL-encoding exactly as it is.** `vipBuildCustom2()` returns a raw
   `eid:...|fbp:...|fbc:...` string; it must be encoded into the query string the same way the
   current code encodes it. The PHP side receives it with `rawurldecode`, so encoded is correct.
2. **Elementor cache.** After changing `_elementor_data`, a LiteSpeed purge is not enough - the
   `_elementor_element_cache` post meta has to be deleted too, or the live page keeps serving
   the old HTML.
3. **Keep writing both `src` and `data-src`.** That double-write exists because of the
   LiteSpeed lazy-load race; v4 changes nothing about it.

**Verify immediately, do not wait for a sale.** On `/havi-elofizetes/`:
`document.cookie` must contain `vip_meta_eid=b<20 hex>`, and the iframe's `src` *and*
`data-src` must carry a `custom2` value starting with `eid:`. Cookie present but no `eid:` in
custom2 means the function swap did not take (or Elementor cache). No cookie means the snippet
is not running. Without this check, a broken bridge only surfaces at the next real purchase as
`EID-HIANYZIK-NEM-PAROSIT`, which can be days away.

**Gate on the browser tag.** Do not re-enable GTM tag 15 at deploy time. v4 writes `eid-hidon`
or `EID-HIANYZIK-NEM-PAROSIT` into every `[OK]` line; re-enable only after several *real*
purchases all read `eid-hidon`. Two data points are not a measurement.

## THE PACKAGE: one file changes (v3, shipped 2026-08-07)

| File | Action |
|------|--------|
| `wp-content/mu-plugins/vip-meta-capi.php` | **replace** with `/Users/macmini/marveen/scripts/vip-meta-capi-v3.php` |
| `wp-content/plugins/salesform_helper/connector.php` | **probably nothing** - confirm with the diff below |

**Lint:** v3 clean on PHP 7.4 and 8.2 (docker `php -l`). Not run against WordPress - no local WP.

> v2 is superseded and must NOT be deployed. It carried an idempotency lock built for a cause
> that measurement has since ruled out; it stays on disk only as a parked implementation.

### There is only one PHP sender, and it is the mu-plugin

Pixel's own count settles this without opening a file. Two purchases produced **4** server
events: one ours, one from the server-side GTM mirror, per purchase. If connector.php were also
sending, our side would contribute two per purchase and the total would be 6, not 4.

Corroborating: the string `[OK] Purchase sent user=#... event_id=sf_...` is emitted inside
`vip_meta_capi_purchase()`, and the `sf_` prefix is built there from SalesForm's `trid`. The
branch that logs, that Meta answered with `events_received=1`, and that carries `value=4990` is
the mu-plugin. connector.php's role is the two-line call into it - the log lives under
`salesform_helper/logs/` only because that is where the mu-plugin was told to write.

So: deploy v3 over the mu-plugin, and expect to change nothing in connector.php.

### Confirmed by the diff, 2026-08-07

`diff -u connector.php.bak-precapi connector.php` is 8 added lines, and they only call the
mu-plugin:

```php
if (function_exists("vip_meta_capi_purchase")) {
    writeLog("[CAPI] " . vip_meta_capi_purchase($formData));
}
```

One implementation, called once. **connector.php is not touched by this deploy.**

**Do not restore `.bak-precapi` - not now, not later.** It predates 2026-08-06 16:29, so it
predates that call. Restoring it removes the only thing that triggers a Purchase, and nothing
sends at all. That failure is silent: the webhook keeps working, payments keep succeeding, the
dataset just goes quiet, and a "the duplication stopped" check would even confirm it.

### Two monitoring signals this call site hands us for free

`writeLog("[CAPI] " . <return value>)` puts the mu-plugin's own return string into
connector.php's log on every webhook. So, in connector's log:

- `[CAPI] skipped-not-live` appearing after deploy means v3's host guard misfired on
  production - i.e. `home_url()` is not what step 0 expected. Fix the constant, do not wait
  for someone to notice the missing conversions.
- **No `[CAPI]` line at all** means `function_exists()` came back false - the mu-plugin is not
  loading. Also silent, also worth alerting on.

## Premise history, 2026-08-07

Two corrections were made during this work, in order:

1. First hypothesis: our own code double-sent through a TOCTOU race in the first-purchase
   guard. **Killed** by Nova's log measurement - one `[OK]` per buyer, `events_received=1`.
2. Then: a second, unidentified sender on the same dataset. **Confirmed** - it is the CAPI
   block inside connector.php, added the same day.

The value question was never ours: both our sends carried `value=4990`. The dataset totalling
4 990 Ft across three purchases means value is lost in deduplication, because the connector
branch presumably sends without one. Removing that branch should fix the value as a side
effect - verify it rather than assume it.

**What survives the correction:** the answer to "since when". The duplication sits on the
server leg, and the server leg did not exist before 2026-08-06 17:05 (Pixel: 28-day pre-CAPI
baseline had zero server events; `server_last_fired_time` still empty on 08-06). Whoever the
second sender is, it started then too. Historical purchase and cost figures are clean, so no
campaign plan needs recalculating. Caveat: the measured window is 28 days, so for anything
older than 2026-07-10 that statement is inference from continuity, not measurement - the
oldest `capi_*.log` filename closes the gap.

## What v3 changes

| # | Change | Why |
|---|--------|-----|
| 0 | Refuses to send unless `home_url()` is production, and unless the payload's `status` is a completed payment | Two guards the mu-plugin did not have. See "Two guards" below. |
| 1 | `client_ip_address` + `client_user_agent`, read from a transient keyed by `_fbp` | Both were 0% on Purchase while 100% on every other event. They cannot come from the webhook request - that caller is SalesForm's server (194.180.16.233), not the buyer. A new `template_redirect` hook stashes the real IP/UA on the two subscription pages. |
| 2 | HUF parsed as digits-only | The old parser read `"4.990"` as **4.99** (verified below). It has not misfired in production yet - both events so far carried 4990 - but it is one payload format away from doing so. |
| 3 | `event_id` fallback no longer contains `time()` | Only applies when SalesForm sends no `trid`, which has not been observed. The old form handed each redelivery a fresh id. One line, closes a latent hole. |
| 4 | `[WARN]` log line when the price is unusable | A 0 Ft conversion drags ROAS down invisibly. |

Measured, PHP 7.4, comparing the two parsers:

```
INPUT                    v3         old
'4990'                 4990         4990
'4 990 Ft'             4990         4990
'4.990'                4990         4.99   <-- defect
'4.990 Ft'             4990         4.99   <-- defect
'4,990'                4990         4.99   <-- defect
'49 900 Ft'           49900        49900
'ingyenes'                0            0
```

On change 1, do not expect too much: better IP/UA raises match quality and makes it likelier
Meta ties the two server events to one person, but Meta's documented deduplication keys are
`event_id`+`event_name` and `fbp`+`event_name`. Treat any effect on the double count as a
bonus, not the fix.

## What was dropped, and why

An idempotency lock around the send. The `_vip_capi_first_purchase` guard is read at the top
and written after a blocking 5s call, so two *simultaneous* deliveries of one webhook would
both get through. That race is real but has never fired, and the duplication has an external
cause. A mutex on a live payment webhook is not worth deploying against a ruled-out
hypothesis. Parked in `vip-meta-capi-v2.php`; revive it only if a second `[OK]` line ever
appears for one `event_id`.

## Not fixable in code

**NovaCapiSelftest** cannot be deleted from the dataset - Meta has no such API. Nothing in the
codebase sends it (grepped, no hits), so it was a one-off and will age out of the windows.
Action is Pixel-side: never wire it to a custom conversion.

## Deploy steps (Nova)

~~Step 0, blocking: print production's `home_url()`.~~ **Done 2026-08-07** - `home` and
`siteurl` are both `https://vip.21napalatt.hu`, exactly what the guard expects. No blocker
left, no constant to change.

1. Back up the current `wp-content/mu-plugins/vip-meta-capi.php`.
2. **Diff prod's `vip-meta-capi.php` against `/Users/macmini/marveen/scripts/vip-meta-capi.php`
   first** - v3 is based on that local copy, and if prod drifted since 08-06 17:14 the drift
   must be carried by hand.
3. Copy v3 into `wp-content/mu-plugins/vip-meta-capi.php`. mu-plugins load automatically.
4. `php -l` it on the server before walking away.
5. Sanity: load `/havi-elofizetes/` once in a browser with a `_fbp` cookie, then confirm a row
   `_transient_vip_capi_ctx_*` exists in `wp_options`. That proves the IP/UA capture arms.
6. **Next real purchase - all three must hold**, and the third is the one that proves the fix:
   - the log line ends `... fbp-megvan ip+ua-megvan`
   - `value=4990`, not `value=0`
   - the dataset shows **one** server Purchase for that sale, not two

### Two guards, both about surviving other people's edits

**Completed payments only.** The SalesForm webhook fires on failed and refused attempts too;
`status` 1 is the successful branch. connector.php gates on that today - but connector.php
ships with the SalesForm plugin, and a vendor update can move or re-add that call anywhere.
Then the gate is gone and nobody edited our code. So v3 checks `status` itself.

Why this one is worth the lines: a failed attempt that sends a Purchase *also* sets
`_vip_capi_first_purchase`, so the same customer's **later real payment sends nothing**. One
false conversion and one lost real one, from a single mistake, and neither is visible in the
count. A missing `status` field passes on purpose - an unfamiliar payload must not silently
stop real sends - but it writes a `[WARN]`. `"1 "` with whitespace is trimmed and passes.

**Production host only.** See the dev leak below.

Neither guard was verified against a live payload - there is no local WordPress. Both are
covered by the deploy check: connector.php's log will carry `[CAPI] sent` on the next real
purchase, and anything else names which guard tripped.

### The dev leak: deploying v3 to production does NOT close it

dev.21napalatt.hu wrote an event into the live dataset on 2026-08-07. A copy of the site
carries a copy of this mu-plugin, the same hardcoded dataset id and its own token - nothing
stopped it.

**The guard only runs where the file runs.** dev has its *own* copy of the mu-plugin, and it is
still the old one. Production refusing to send from a non-production host says nothing about
what dev's copy does. To actually close it, one of:

- put v3 on dev as well - it then refuses to send from dev, by its own guard, and logs
  `[SKIP] not the live host` when it tries; or
- remove the mu-plugin from dev entirely.

The first is better: it turns dev into a detector instead of a blind spot.

And even then, this covers **our server leg only**. If the dev site also serves the GTM
container or a raw pixel snippet, the browser leg keeps firing from dev - that needs a hostname
exclusion in the container, which is not PHP work.

**Which branch was the stray event? There is a cheaper test than a Meta-side breakdown.** Look
at dev's own `wp-content/plugins/salesform_helper/logs/capi_*.log`. An `[OK] Purchase sent` line
there means it was our server leg. No such line - or no log directory at all - means it was the
browser leg, and the fix is container-side.

Rollback is the two backup files. v3 adds no schema and no state beyond a one-day transient.

### After deploy, one thing is still open

The browser-side Purchase tag (GTM tag 15) sends no `value` and no `eventID`. With a single
server sender it should collapse on `fbp`+`event_name`, so it is no longer the urgent problem -
but if a sale ever shows up at 0 Ft, that tag winning the deduplication is the first suspect.

## How the second sender was found (historical)

`/Users/macmini/marveen/scripts/vip-capi-masodik-kuldo-kereses.php` - read-only, SELECTs and
file reads only. Copy to the account root and run `php vip-capi-masodik-kuldo-kereses.php`.
Nova ran it on 2026-08-07 and section 6 named both senders directly.

It enumerates active plugins and mu-plugins, `wp_options` rows whose *value* contains the
dataset id, Facebook/CAPI-named options, the SalesForm helper's own settings, every `.php`
under `wp-content` that touches `graph.facebook.com` or the dataset id, and Facebook-ish cron
hooks. It prints option **names** and file:line only - never values, never matched lines,
since access tokens live next to exactly these keys.

Keep it: it is the regression check. Re-run it after any SalesForm plugin update, because a
vendor update can put a CAPI block back into connector.php and nobody would notice until the
count doubles again.

If sections 3-6 ever come back empty, the second sender is not on this server, and the question
has to be closed from the Meta side - Events Manager names the integration per received event.
