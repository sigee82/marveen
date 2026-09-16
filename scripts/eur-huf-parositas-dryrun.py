#!/usr/bin/env python3
"""DRY RUN for the EUR-invoice / HUF-payment matching rule. Writes NOTHING.

PUBLIC REPO: this repository is public, so no client name, invoice number, bank
account or payer appears in this file. Every such value is read from the database
at run time and only ever printed locally. Keep it that way when editing.

Two foreign clients are invoiced in EUR and pay in HUF, so amount equality never
holds and the invoice ages into 'expired' while the money is in the bank. This
script measures what a matching rule WOULD do, over the whole 2026 traffic, and
counts the ambiguous cases separately -- a rule that mismatches silently is worse
than the current visible failure.

TWO CORRECTIONS TO THE HANDED-DOWN SPEC, both measured (see --meres):

1. THE ANCHOR IS document_date, NOT fulfillment_date. The four observed offsets
   (+1, +4, -3, +1) only reproduce against document_date; against fulfillment_date
   the same four payments sit at -4, -7, -7, -11, so the specified -7..+14 window
   would drop one of the four invoices the rule exists to fix.

2. THE STATED RATE BAND EXCLUDES ITS OWN SOURCE OBSERVATION. 74246/210 =
   353.5524, below the quoted lower bound of 353.6 (the quote was rounded to one
   decimal). Applied strictly, the band drops a fourth case. The bounds here are
   the measured extremes with an explicit margin, and --sav shows the sensitivity.

The partner filter is a PRECONDITION, not a refinement: without it the amount+date
window alone pulls in credits from unrelated payers that happen to land on a
similar amount and date. Run --kontroll to reproduce it against live data; the
payers are deliberately not named here, see the PUBLIC REPO note below.

finance_transactions.amount is stored as TEXT, so every numeric comparison casts
first -- the raw form returns zero rows silently instead of erroring.

WHERE THIS RULE IS *NOT* WIRED IN: nowhere. The matcher that owns
matched_transaction_id/match_status does not live in this repository -- neither
column appears anywhere in it. This script reads Summa's snapshot of
napalatt_innoworx_prod, so it measures a copy; switching the rule on would touch
the live InnoWorx system, which is a separate decision and a separate codebase.
Today this file is the only written description of the rule. Do not go looking
for the place it is enabled.

BASELINE, RECORDED BEFORE ANY CHANGE (so the check afterwards is the receivables
report, not the matcher's own feedback about itself):
  2026 EUR receivables today : 4 invoices / 840 EUR  -> must go to 0
  2026 HUF receivables today : 110 invoices / 18,528,516 HUF -> must stay UNCHANGED
If the HUF side moves too, the rule reached further than it was meant to.
"""
import argparse
import sqlite3
import unicodedata
from datetime import date, timedelta

DB = '/Users/macmini/marveen/agents/summa/data/finance.sqlite'

ANCHOR = 'document_date'
WINDOW_BACK, WINDOW_FWD = 7, 14
RATE_LO, RATE_HI = 352.0, 359.0      # measured 353.55 .. 357.46, plus ~0.4% margin
SENTINEL = 888888                    # "confirmed by hand, no bank row behind it"


def norm(s):
    """Accent- and case-insensitive form: the bank writes names unaccented and in
    upper case, the invoice keeps the accents, so neither side matches raw."""
    return ''.join(c for c in unicodedata.normalize('NFD', s or '')
                   if unicodedata.category(c) != 'Mn').upper()


def connect():
    con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    con.execute('CREATE TEMP VIEW tx AS SELECT t.*, CAST(t.amount AS REAL) AS amt FROM finance_transactions t')
    con.execute('CREATE TEMP VIEW doc AS SELECT d.*, CAST(d.total_gross_local AS REAL) AS brutto FROM billingo_documents d')
    return con


def candidates(con, inv_id, partner, eur, anchor_day, *, partner_filter=True,
               lo=RATE_LO, hi=RATE_HI, back=WINDOW_BACK, fwd=WINDOW_FWD):
    """Bank credits that could pay this invoice. The name test requires EVERY token
    of the partner name to appear, which is what separates the two sisters -- and
    is order-insensitive, because the bank writes both 'KRISZTINA SZAMELOVA' and
    'SZAMELOVA KRISZTINA'."""
    lo_day = (anchor_day - timedelta(days=back)).isoformat()
    hi_day = (anchor_day + timedelta(days=fwd)).isoformat()
    # partner_account (the IBAN) is a STRONGER discriminator than the description:
    # each of the two clients pays from a stable account of her own, and one of them
    # changed accounts once mid-year -- so it separates them exactly, where the free
    # text does not. It is deliberately NOT a decision signal yet -- the name-token
    # set separates today's two clients on its own, and an unused second criterion
    # cannot be shown to work. It is selected and printed so it stays visible, and it
    # is the fallback for the day two clients share a first name, or the bank changes
    # how it writes the description. Not an oversight.
    tokens = [t for t in norm(partner).split() if len(t) > 2]
    out = []
    for tid, tdate, amt, acct, desc in con.execute(
            """SELECT id, substr(date,1,10), amt, partner_account, description FROM tx
               WHERE type='income' AND currency='HUF' AND substr(date,1,10) BETWEEN ? AND ?""",
            (lo_day, hi_day)):
        if not eur:
            continue
        rate = amt / eur
        if not (lo <= rate <= hi):
            continue
        if partner_filter and not all(t in norm(desc) for t in tokens):
            continue
        out.append((tid, tdate, amt, rate, acct, desc))
    return out


def open_eur_invoices(con):
    return con.execute(
        f"""SELECT id, document_number, partner_name, brutto, {ANCHOR}, payment_status
            FROM doc
            WHERE currency='EUR' AND {ANCHOR} >= '2026-01-01'
              AND COALESCE(match_status,'none') <> 'confirmed'
              AND COALESCE(matched_transaction_id, 0) <> ?
            ORDER BY {ANCHOR}""", (SENTINEL,)).fetchall()


def run(partner_filter=True, lo=RATE_LO, hi=RATE_HI, verbose=True):
    con = connect()
    one = ambiguous = none = 0
    for iid, num, partner, eur, anchor, pstatus in open_eur_invoices(con):
        cands = candidates(con, iid, partner, eur, date.fromisoformat(anchor),
                           partner_filter=partner_filter, lo=lo, hi=hi)
        if len(cands) == 1:
            one += 1
            if verbose:
                t = cands[0]
                print(f'  EGYERTELMU  {num:<18} {partner:<22} {eur:>7.0f} EUR  -> tx {t[0]} '
                      f'{t[1]} {t[2]:>9.0f} Ft  arf {t[3]:.2f}')
        elif len(cands) > 1:
            ambiguous += 1
            if verbose:
                print(f'  TOBBERTELMU {num:<18} {partner:<22} {len(cands)} jelolt -> EMBER DONTI')
                for t in cands:
                    print(f'                  tx {t[0]} {t[1]} {t[2]:>9.0f} Ft  arf {t[3]:.2f}  {t[5][:52]}')
        else:
            none += 1
    return one, ambiguous, none


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kontroll', action='store_true', help='partner-szures NELKUL (negativ kontroll)')
    ap.add_argument('--sav', action='store_true', help='arfolyam-sav erzekenyseg')
    a = ap.parse_args()

    if a.sav:
        print('  arfolyam-sav erzekenyseg (partner-szuressel):')
        for lo, hi in [(353.6, 357.5), (353.5, 357.5), (352.0, 359.0), (350.0, 360.0), (340.0, 370.0)]:
            o, amb, _ = run(lo=lo, hi=hi, verbose=False)
            flag = '  <-- a leirt sav: EGY ESETET ELVESZIT' if (lo, hi) == (353.6, 357.5) else ''
            print(f'    {lo:6.1f} - {hi:6.1f}   egyertelmu: {o}   tobbertelmu: {amb}{flag}')
        return

    pf = not a.kontroll
    print(f'  SZARAZ FUTAS -- semmit nem ir. partner-szures: {"IGEN" if pf else "NEM (negativ kontroll)"}')
    print(f'  horgony: {ANCHOR}   ablak: -{WINDOW_BACK}..+{WINDOW_FWD} nap   sav: {RATE_LO}-{RATE_HI} Ft/EUR\n')
    one, amb, none = run(partner_filter=pf)
    print(f'\n  EGYERTELMU  : {one}')
    print(f'  TOBBERTELMU : {amb}   (ezek ember ele mennek, nem parosodnak)')
    print(f'  NINCS TALALAT: {none}')


if __name__ == '__main__':
    main()
