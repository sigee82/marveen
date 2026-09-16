#!/usr/bin/env python3
"""Re-apply the inbound reply-context patch to the official Telegram channel plugin.

WHY THIS EXISTS
---------------
Telegram sends `reply_to_message` on every quote-reply. The official plugin reads it
in exactly one place (to decide whether a message is addressed to the bot) and then
drops it, so the model never learns what the user replied to. Zsolt hit this on
2026-09-10 and it cost several round-trips ("nem latod, hogy mire replyztem??").

The upstream fix is reported separately. This script is the local bridge, and it is
written to SURVIVE PLUGIN UPDATES: it runs at SessionStart, finds every copy of the
plugin's server.ts, and re-inserts the patch into any copy that lost it.

DESIGN RULES
------------
- IDEMPOTENT: a file that already carries MARKER is left alone.
- LOUD ON DRIFT: if a copy has neither the marker nor the anchor, the upstream code
  changed shape. The script does NOT guess and does NOT edit -- it reports and exits
  non-zero, so a silently-broken patch cannot masquerade as a working one.
- READ-BACK: every write is verified by re-reading the file.
- The quoted text goes into META, not into content -- same treatment as image_path,
  because the quoted text is sender-controlled and must not look like an instruction.
"""

import os
import sys

HOME = os.path.expanduser("~")
ROOTS = [
    os.path.join(HOME, ".claude/plugins/cache/claude-plugins-official/telegram"),
    os.path.join(HOME, ".claude/plugins/marketplaces/claude-plugins-official/external_plugins/telegram"),
]

MARKER = "nova-reply-context-patch"
ANCHOR = "        ...(msgId != null ? { message_id: String(msgId) } : {}),\n"

PATCH = (
    "        // " + MARKER + " -- see scripts/telegram-reply-context-patch.py\n"
    "        // Telegram sends reply_to_message on quote-replies; upstream drops it.\n"
    "        // META, not content: the quoted text is sender-controlled.\n"
    "        ...(ctx.message?.reply_to_message ? {\n"
    "          reply_to_message_id: String(ctx.message.reply_to_message.message_id),\n"
    "          reply_to_user: String(\n"
    "            (ctx.message.reply_to_message as any).from?.username\n"
    "            ?? (ctx.message.reply_to_message as any).from?.id\n"
    "            ?? '',\n"
    "          ),\n"
    "          reply_to_text: String(\n"
    "            (ctx.message.reply_to_message as any).text\n"
    "            ?? (ctx.message.reply_to_message as any).caption\n"
    "            ?? '',\n"
    "          ).slice(0, 900),\n"
    "        } : {}),\n"
)


def server_files():
    out = []
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        direct = os.path.join(root, "server.ts")
        if os.path.isfile(direct):
            out.append(direct)
        for name in sorted(os.listdir(root)):
            cand = os.path.join(root, name, "server.ts")
            if os.path.isfile(cand):
                out.append(cand)
    return out


def main():
    files = server_files()
    if not files:
        print("DRIFT: egyetlen telegram server.ts sem talalhato a vart utakon.", file=sys.stderr)
        for r in ROOTS:
            print("  vizsgalt gyoker: %s" % r, file=sys.stderr)
        return 2

    patched, already, drifted = [], [], []
    for path in files:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        short = path.replace(HOME + "/.claude/plugins/", "")

        if MARKER in src:
            already.append(short)
            continue
        if src.count(ANCHOR) != 1:
            drifted.append((short, src.count(ANCHOR)))
            continue

        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src.replace(ANCHOR, ANCHOR + PATCH, 1))

        # read-back: a sikeres iras nem bizonyitek, a visszaolvasott fajl az
        with open(path, encoding="utf-8") as fh:
            back = fh.read()
        if MARKER not in back or "reply_to_message_id" not in back:
            print("HIBA: a folt beirasa utan sem talalhato a fajlban: %s" % short, file=sys.stderr)
            return 3
        patched.append(short)

    # CSENDES A NO-OP AGON. Ez a szkript minden session-inditaskor lefut az egesz
    # flottan; ha a mar-patchelt allapotot is kiirna, harom sor zajt tenne minden
    # egyes indulasba, es par nap alatt senki nem nezne oda. Csak a VALTOZAS es a
    # DRIFT hangos. (`-v` kikapcsolja ezt, kezi ellenorzeshez.)
    verbose = "-v" in sys.argv
    for p in patched:
        print("PATCHELVE: %s" % p)
    if verbose:
        for p in already:
            print("mar patchelt: %s" % p)
    for p, n in drifted:
        print(
            "DRIFT: %s -- a horgony %d-szer szerepel (1 kellene). A plugin kodja "
            "megvaltozott, NEM nyultam hozza. Nezd meg a meta-epitest a "
            "server.ts-ben." % (p, n),
            file=sys.stderr,
        )

    if drifted:
        return 4
    if patched:
        print(
            "\nA folt a KOVETKEZO csatorna-ujrainditaskor lep eletbe "
            "(a bot kulon `bun server.ts` processz)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
