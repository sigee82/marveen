#!/usr/bin/env python3
"""Levél-figyelő (szamlagyujtes v2): a postafiókokban érkező számla-PDF-eket a tábla soraihoz köti. Ágens nélkül fut.

Zsolt döntése (TG 18663): gépi úton, legfeljebb napi 3 futással; ami így nem lesz meg, azzal Signal foglalkozik.

Menet:
- IMAP, CSAK OLVASVA (readonly SELECT: a levelek olvasottsága nem változik, semmit nem töröl, nem mozgat):
  info@innogroup.hu (Eszter) és szigeti.zsolt@innogroup.hu, az utolsó NAP napban érkezett levelek, minden mappában
  a Sent/Drafts/Spam kivételével.
- Számlakép-jelölt egy levélben: PDF-melléklet, vagy ismert számlázó letöltő-linkje (Billingo document-access,
  szamlazz.hu vevői fiók).
- Bekötés CSAK ha a PDF szövegében (pdftotext) benne van egy számlakép nélküli sor sorszáma (min. 6 karakter,
  írásjelek nélkül), és pontosan EGY ilyen sor van. Ekkor a PDF a cég/év/hónap mappába kerül, a Számla cella linket kap.
- A már feldolgozott leveleket (fiók, mappa, UIDVALIDITY, UID) megjegyzi: state/level-figyelo.json.
- A futás végén a még mindig képnélküli sorokból az ÚJAKAT (amiről Signal még nem kapott listát) egy
  inter-agent üzenetben átadja Signalnak (--signal kapcsolóval; a napi futás este adja meg).

Futtatás:  python3 level_figyelo.py [--dry] [--napok 45] [--signal]
"""
import argparse
import datetime
import email
import email.header
import email.utils
import html
import imaplib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

import config as C
import gapi
import kinyer
import tabla

STATE = os.path.join(C.STATE_DIR, 'level-figyelo.json')
ACCOUNTS = [('eszter', 'info@innogroup.hu', 'MAIL_ESZTER_PASSWORD'),
            ('zsolt', 'szigeti.zsolt@innogroup.hu', 'MAIL_ZSOLT_PASSWORD')]
HOST = 'mail.innogroup.hu'
RECHECK_DAYS = 14
SKIP_FOLDERS = re.compile(r'(sent|draft|spam|junk|elk[uü]ld|piszkozat|lev[eé]lszem[eé]t)', re.I)
LINKS = [
    (re.compile(r'https://app\.billingo\.hu/document-access/(?:default/)?([A-Za-z0-9]{20,})'),
     lambda m: f'https://app.billingo.hu/document-access/{m.group(1)}/download'),
]
SZAMLAZZ = re.compile(r'https://www\.szamlazz\.hu/szamla/fiok/[A-Za-z0-9]+\?szfejguid=[A-Za-z0-9]+')
# subject of a mail that announces an invoice even without a PDF attachment
INVOICE_SUBJ = re.compile(r'sz[aá]ml[aá]|sz[aá]mla|invoice|receipt|nyugta|bizonylat|rechnung|d[ií]jbek[eé]r', re.I)
# ...but these are about an invoice, not invoices: payment confirmations, reminders, discussions
NOT_INVOICE_SUBJ = re.compile(r'sikeres (sz[aá]mla)?befizet|sikeres fizet|fizet[eé]si eml[eé]keztet|'
                              r'sz[aá]mlasz[aá]m.*v[aá]ltoz|^\s*(re|v[aá]):', re.I)
# ad-spend receipts (Meta/Google Ads, dozens a week per client account) are kept out until Zsolt decides
# whether they belong in the tables (2026-10-10: 48 Meta + 7 Google Ads receipts in October, none in a table)
SKIP_SENDERS = re.compile(r'business-updates\.facebook|facebookmail|payments-noreply@google|'
                          r'@noreply\.telekom\.hu|@telekom\.hu|@one\.hu', re.I)   # Telekom/One: the portal job fetches them
HU_TAX = re.compile(r'(?<!\d)\d{8}-\d-\d{2}(?!\d)')     # Hungarian tax number: 12345678-1-12
TRACK = re.compile(r'https?://[A-Za-z0-9.-]*(?:awstrack\.me|ses|track|click)[^\s"\'<>]*', re.I)


def n(x):
    return re.sub(r'[^0-9a-z]', '', str(x or '').lower())


def secret(sid):
    return subprocess.run(['node', '--input-type=module', '-e',
                           "import { getSecret } from '/Users/macmini/marveen/dist/web/vault.js';"
                           f"process.stdout.write(getSecret('{sid}') || '')"], capture_output=True, text=True, check=True).stdout


def dec(s):
    out = ''
    for part, enc in email.header.decode_header(s or ''):
        if isinstance(part, bytes):
            # a header can name a charset Python does not know ("unknown-8bit", 2026-10-27): fall back to utf-8
            try:
                out += part.decode(enc or 'utf-8', 'replace')
            except LookupError:
                out += part.decode('utf-8', 'replace')
        else:
            out += part
    return out


def has_number(raw, num):
    """The invoice number as a standalone token in the PDF text (separators may differ: 'BT / 2026-1' vs 'BT/2026-1'),
    not as the tail of a longer number ('A24700033' inside 'V/A24700033' or '...12345' inside '9912345')."""
    chars = [c for c in str(num) if c.isalnum()]
    if not chars:
        return False
    pat = r'(?<![0-9A-Za-z/])' + r'[\s./-]*'.join(map(re.escape, chars)) + r'(?![0-9A-Za-z])'
    return re.search(pat, raw, re.I) is not None


def pdf_text(data):
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(data)
        f.flush()
        return subprocess.run(['pdftotext', '-layout', f.name, '-'], capture_output=True, text=True).stdout


def fetch(url, limit=15_000_000):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (szamlagyujtes)'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.geturl(), r.headers.get('Content-Type', ''), r.read(limit)


def links_to_pdfs(body):
    """Known invoicing services: return (url, pdf bytes) for every downloadable invoice behind a link in the mail."""
    found = []
    urls = set(re.findall(r'https?://[^\s"\'<>]+', body))
    for u in list(urls):                       # tracking redirect (ses/awstrack): follow once to see the target
        if TRACK.match(u) and ('billingo' in body.lower() or 'szamlazz' in body.lower()):
            try:
                final, _, _ = fetch(u, 2000)
                urls.add(final)
            except Exception:
                pass
    for u in urls:
        for rx, mk in LINKS:
            m = rx.match(u)
            if m:
                try:
                    _, ct, data = fetch(mk(m))
                    if 'pdf' in ct:
                        found.append((u, data))
                except Exception as e:
                    print(f'  link-hiba {u[:60]}: {e}')
        if SZAMLAZZ.match(u):
            try:
                _, _, html = fetch(u)
                for href in re.findall(rb'href="(/szamla/\?action=szamlapdf[^"]+)"', html)[:1]:
                    _, ct, data = fetch('https://www.szamlazz.hu' + href.decode().replace('&amp;', '&'))
                    if 'pdf' in ct:
                        found.append((u, data))
            except Exception as e:
                print(f'  link-hiba {u[:60]}: {e}')
    return found


# a PDF is an INVOICE only if it names its own number: 'számla sorszáma', 'sorszám', 'invoice number'... -- a bare
# 'számla' is in every bank statement, notice and certificate (measured 2026-10-08: 31 hits, most of them not invoices)
INVOICE_WORD = re.compile(r'sz[aá]mla\s*sorsz[aá]m|sorsz[aá]m\s*:|(?<!bank)(?<!Bank)(?<!foly[oó])sz[aá]mlasz[aá]m\s*:|invoice\s*(number|no\b|#)|'
                          r'receipt\s*(number|no\b|#)|rechnungs?nummer', re.I)


STATEMENT = re.compile(r'banksz[aá]mla[\s-]*kivonat|sz[aá]mlakivonat|bank\s*account\s*statement|account\s*statement|'
                       r'kontoauszug', re.I)


def send_signal(msg):
    tok = open('/Users/macmini/marveen/store/.dashboard-token').read().strip()
    req = urllib.request.Request('http://localhost:3420/api/messages', method='POST',
                                 data=json.dumps({'from': 'nova', 'to': 'signal', 'content': msg}).encode(),
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + tok})
    urllib.request.urlopen(req, timeout=20)


CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


def mail_pdf(msg):
    """The mail itself as a PDF. NOT used as an invoice image: Zsolt 2026-10-10, 'what you downloaded is not the
    Canva invoice, only the e-mail' -- kept for diagnostics only. Remote content stays off."""
    import shutil
    htm = ''
    for part in msg.walk():
        if part.get_content_type() == 'text/html' and not part.get_filename():
            htm = (part.get_payload(decode=True) or b'').decode(part.get_content_charset() or 'utf-8', 'replace')
            break
    if not htm:
        for part in msg.walk():
            if part.get_content_type() == 'text/plain' and not part.get_filename():
                txt = (part.get_payload(decode=True) or b'').decode(part.get_content_charset() or 'utf-8', 'replace')
                htm = '<pre style="white-space:pre-wrap;font-family:sans-serif">' + html.escape(txt) + '</pre>'
                break
    htm = re.sub(r'(?is)<script.*?</script>', '', htm)
    htm = re.sub(r'(?i)(<img[^>]*?)\ssrc=("[^"]*"|\'[^\']*\')', r'\1', htm)
    head = ''.join(f'<div><b>{k}:</b> {html.escape(dec(msg[k] or ""))}</div>' for k in ('From', 'Date', 'Subject'))
    page = (f'<!doctype html><meta charset="utf-8"><div style="font:12px sans-serif;border-bottom:1px solid #999;'
            f'padding:6px;margin-bottom:8px">{head}</div>' + htm)
    d = tempfile.mkdtemp(prefix='levelpdf-')
    try:
        src, out = os.path.join(d, 'mail.html'), os.path.join(d, 'mail.pdf')
        open(src, 'w').write(page)
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-first-run', f'--user-data-dir={d}/prof',
                        '--blink-settings=imagesEnabled=false', '--disable-javascript', '--no-pdf-header-footer',
                        f'--print-to-pdf={out}', 'file://' + src], capture_output=True, timeout=90)
        return open(out, 'rb').read() if os.path.exists(out) and os.path.getsize(out) > 1000 else None
    except Exception as e:
        print(f'  level-PDF hiba: {e}')
        return None
    finally:
        shutil.rmtree(d, ignore_errors=True)


# uids whose outcome is final although no row was bound (an invoice older than START_MONTH): marked seen at once, so a
# young mail is not re-extracted (a model call) three times a day for 14 days -- 2026-10-13: uid 1089, a 2022-07-29
# szamlazz.hu invoice, came back every run, once judged 'nem szamla', once 'regi szamla' (the model is not stable)
FINAL = set()


def queue_or_report(felvesz, report, known, text, data, ext, entry):
    """Fields read from the text and checked against it (kinyer.py): queued for recording; anything else -> Signal."""
    box = entry[3]
    hint = 'innovative' if re.search(r'innogroup|innovative', box, re.I) else \
        'innoworx' if re.search(r'innoworx', box, re.I) else None
    # deterministic first: if every date in the document is older than START_MONTH, it is an old invoice whatever the
    # model says (uid 1089 got 'nem szamla' and 'regi szamla' on alternate runs) -- final, no model call, no Signal
    dates = sorted(f'{y}-{m}' for y, m in re.findall(r'\b(20\d\d)[.\-/] ?(0[1-9]|1[0-2])[.\-/] ?[0-3]\d\b', text or ''))
    if dates and dates[-1] < C.START_MONTH:
        print(f'  regi dokumentum (legujabb datum {dates[-1]}), kihagyva -- vegleges, latottnak jelolve')
        FINAL.add(entry[4])
        return False
    f, why = kinyer.extract(text, hint)
    if why:
        print(f'  kinyeres elutasitva: {why}')
        # a 'not an invoice' verdict on a mail that sits in the TRASH, without any PDF (2026-10-14: uid 42160, a
        # 'Matricas Windows 11 Pro' ad) is noise for Signal: final, seen, not reported. Any other folder, or a PDF, or
        # a different rejection reason (wrong buyer, number mismatch) still goes to Signal.
        # a bank statement the model also rejected (2026-10-25: CIB 'Bank account statement', OTP 'BANKSZÁMLAKIVONAT'
        # of other companies, three in one run) is never an invoice: final, not reported. The model has the last word,
        # the keyword only silences its 'no' -- a statement the model reads as an invoice still goes on.
        if 'nem szamla' in why and STATEMENT.search(text or ''):
            print('  bankszamlakivonat, a modell szerint sem szamla -- vegleges, Signalnak nem megy')
            FINAL.add(entry[4])
            return False
        if re.search(r'(^|\.)trash$', box, re.I) and data is None and 'nem szamla' in why:
            print('  kukaban levo nem-szamla level, PDF nelkul -- vegleges, Signalnak nem megy')
            FINAL.add(entry[4])
            return False
        report.append(entry[:1] + (f'{entry[1]} -- gepi felvetel elutasitva: {why}',) + entry[2:])
        return False
    if f['kelte'][:7] < C.START_MONTH:  # the tables start at START_MONTH; older invoices are not tracked
        print(f'  regi szamla ({f["kelte"]}), kihagyva -- vegleges, latottnak jelolve')
        FINAL.add(entry[4])
        return False
    if n(f['sorszam']) in known:       # already in a table (e.g. both mailboxes got it): nothing to record
        print(f'  mar fent: {f["sorszam"]}')
        return False
    if ext == '.levelpdf':             # the invoice is the mail itself: its PDF is the document
        data, ext = mail_pdf(data), '.pdf'
    known.add(n(f['sorszam']))
    print(f'  FELVESZEM {f["entitas"]} {f["partner"][:40]} {f["sorszam"]} {f["osszeg"]} {f["penznem"]} {f["kelte"]}')
    felvesz.append((f, data, ext, entry))
    return True


def record(felvesz, report, dry):
    """szamla_felvesz.py for each queued invoice (it de-duplicates, files the PDF, reads the row back)."""
    for f, data, ext, entry in felvesz:
        _, why, acc, box, uid, msg, fn = entry
        cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'szamla_felvesz.py'),
               '--entitas', f['entitas'], '--partner', f['partner'], '--sorszam', f['sorszam'],
               '--osszeg', str(f['osszeg']), '--penznem', f['penznem'], '--kelte', f['kelte'],
               '--forras', f'{acc}/{box} uid {uid} (level_figyelo, gepi kinyeres)',
               '--megjegyzes', f'Levél: {dec(msg["From"])[:60]} | {dec(msg["Subject"])[:80]}'
                               + ('' if data else ' | Számlakép nincs: a levél csak értesítő, a számla a szolgáltató fiókjában van')]
        if f.get('hatarido'):
            cmd += ['--hatarido', f['hatarido']]
        if f.get('bankszamla'):
            cmd += ['--bankszamla', f['bankszamla']]
        if f.get('kartyas'):
            cmd += ['--statusz', C.S_CARD]
        if dry:
            cmd.append('--dry')
        tmp = None
        try:
            if data:
                tmp = tempfile.NamedTemporaryFile(suffix=ext or '.pdf', delete=False)
                tmp.write(data)
                tmp.close()
                cmd += ['--pdf', tmp.name]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if p.returncode != 0:
                raise RuntimeError((p.stderr or p.stdout).strip()[-300:])
            print(f'FELVEVE   {p.stdout.strip()[:300]}')
        except Exception as e:
            print(f'FELVETEL HIBA {f["sorszam"]}: {e}')
            report.append(entry[:1] + (f'{why} -- gepi felvetel hiba: {e}',) + entry[2:])
        finally:
            if tmp:
                os.unlink(tmp.name)


def missing_rows(ses, reg):
    out = []
    for ent in C.ENTITIES:
        ssid = reg.get(f'sheet:{ent["key"]}:{datetime.date.today().year}')
        if not ssid:
            continue
        ses._sheet(ent, str(datetime.date.today().year), create=False)
        for tab, rows in ses.rows(ssid).items():
            for i, r in enumerate(rows):
                if r[C.COL['Forrás-azonosító']] and not str(r[C.COL['Számla']] or '').strip() and len(n(r[2])) >= 6:
                    out.append((ent, ssid, tab, i, r))
    return out


def signal_rows(todo, sent):
    """-> (rows to hand to Signal, rows skipped because their invoice only exists in the supplier's portal)."""
    new = [t for t in todo if t[4][C.COL['Forrás-azonosító']] not in sent]
    return [t for t in new if not C.portal_only(t[4][1])], [t for t in new if C.portal_only(t[4][1])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--napok', type=int, default=45)
    ap.add_argument('--signal', action='store_true', help='a maradek uj hianyokat atadja Signalnak')
    ap.add_argument('--mind', action='store_true', help='a mar feldolgozott leveleket is ujranezi (atfesules)')
    a = ap.parse_args()
    state = json.load(open(STATE)) if os.path.exists(STATE) else {'seen': {}, 'signal_sent': []}
    ses = tabla.Session(dry=a.dry)
    reg = tabla._load()
    todo = missing_rows(ses, reg)
    known = set()                      # every row's invoice number, linked or not (an invoice already in a table)
    for ent in C.ENTITIES:
        ssid = reg.get(f'sheet:{ent["key"]}:{datetime.date.today().year}')
        if ssid:
            for rows in ses.rows(ssid).values():
                known |= {n(r[2]) for r in rows if r[C.COL['Forrás-azonosító']] and len(n(r[2])) >= 6}
    report = []
    felvesz = []                       # invoices with no row: recorded after ses.flush() (szamla_felvesz.py)
    canva_nova = []                    # Canva invoice numbers: Nova fetches the real invoice in the browser
    print(f'kepnelkuli sor: {len(todo)}')
    since = (datetime.date.today() - datetime.timedelta(days=a.napok)).strftime('%d-%b-%Y')
    stat = {'level': 0, 'pdf': 0, 'kotve': 0, 'nem_egyertelmu': 0}
    for acc, user, sid in ACCOUNTS:
        im = imaplib.IMAP4_SSL(HOST, 993)
        im.login(user, secret(sid))
        typ, boxes = im.list()
        for raw in boxes or []:
            line = raw.decode('utf-8', 'replace')
            m = re.match(r'\((?P<fl>[^)]*)\) "(?P<d>[^"]*)" (?P<name>.+)$', line)
            if not m or '\\Noselect' in m.group('fl'):
                continue
            box = m.group('name').strip()
            if SKIP_FOLDERS.search(box):
                continue
            typ, st = im.status(box, '(UIDVALIDITY)')
            mv = re.search(rb'UIDVALIDITY (\d+)', st[0] if st and st[0] else b'')
            uv = mv.group(1).decode() if mv else '0'
            typ, _ = im.select(box, readonly=True)
            if typ != 'OK':
                continue
            key = f'{acc}|{box}|{uv}'
            seen = set() if a.mind else set(state['seen'].get(key, []))
            typ, data = im.uid('search', None, f'SINCE {since}')
            uids = [u.decode() for u in (data[0].split() if data and data[0] else [])]
            uids = [u for u in uids if u not in seen]
            # only the mails that can carry an invoice: a PDF part (BODYSTRUCTURE, no body download) or an invoicing link
            cand = set()
            for i0 in range(0, len(uids), 200):
                chunk = ','.join(uids[i0:i0 + 200])
                typ, bs = im.uid('fetch', chunk, '(BODYSTRUCTURE)')
                for item in bs or []:
                    raw = item if isinstance(item, bytes) else b''.join(x for x in item if isinstance(x, bytes))
                    mu = re.search(rb'UID (\d+)', raw)
                    if mu and (b'"pdf"' in raw.lower() or b'.pdf"' in raw.lower()):
                        cand.add(mu.group(1).decode())
            for word in ('document-access', 'szamlazz.hu'):
                typ, data = im.uid('search', None, f'SINCE {since} TEXT "{word}"')
                cand |= {u.decode() for u in (data[0].split() if data and data[0] else [])}
            # an invoice can come WITHOUT a PDF: only a login link (Canva, Stripe), the data in the body, or a phone
            # photo (Eszter's 'Szamla obi', 2026-10-08). Those mails are candidates by their SUBJECT (2026-10-10).
            hint = set()
            for i0 in range(0, len(uids), 200):
                chunk = ','.join(uids[i0:i0 + 200])
                typ, hs = im.uid('fetch', chunk, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])')
                for item in hs or []:
                    if not isinstance(item, tuple):
                        continue
                    mu = re.search(rb'UID (\d+)', item[0])
                    h = email.message_from_bytes(item[1])
                    subj, frm = dec(h['Subject'] or ''), dec(h['From'] or '')
                    if mu and INVOICE_SUBJ.search(subj) and not NOT_INVOICE_SUBJ.search(subj) \
                            and not SKIP_SENDERS.search(frm):
                        hint.add(mu.group(1).decode())
            cand |= hint
            print(f'  {acc}/{box}: {len(uids)} uj level, {len(cand & set(uids))} jelolt', flush=True)
            for uid in uids:
                if uid not in cand:
                    seen.add(uid)
                    continue
                if uid in seen:
                    continue
                typ, msgdata = im.uid('fetch', uid, '(BODY.PEEK[])')       # PEEK: the \\Seen flag stays untouched
                if typ != 'OK' or not msgdata or not msgdata[0]:
                    continue
                msg = email.message_from_bytes(msgdata[0][1])
                stat['level'] += 1
                # a mail can arrive BEFORE its row exists (NAV/Billingo lag of a few days): an unmatched candidate is
                # re-checked on every run until it is RECHECK_DAYS old, only then marked as done
                try:
                    sent = email.utils.parsedate_to_datetime(msg['Date']).date()
                except Exception:
                    sent = datetime.date.today()
                young = (datetime.date.today() - sent).days < RECHECK_DAYS
                bound_any = False
                pdfs, body = [], ''
                for part in msg.walk():
                    ct = part.get_content_type()
                    fn = dec(part.get_filename() or '')
                    if ct == 'application/pdf' or fn.lower().endswith('.pdf'):
                        pdfs.append((fn, part.get_payload(decode=True) or b''))
                    elif ct in ('text/plain', 'text/html') and not part.get_filename():
                        body += (part.get_payload(decode=True) or b'').decode(part.get_content_charset() or 'utf-8', 'replace')
                pdfs += [(f'link:{u[:50]}', d) for u, d in links_to_pdfs(body)]
                inv_pdf = False
                ptexts = []                    # (fn, bytes, text) of every PDF: a no-row invoice is read from these
                for fn, data in pdfs:
                    stat['pdf'] += 1
                    raw_text = pdf_text(data)
                    ptexts.append((fn, data, raw_text))
                    inv_pdf = inv_pdf or bool(INVOICE_WORD.search(raw_text))
                    text = n(raw_text)
                    # short numbers can occur by chance in any PDF: below 10 characters the amount must be there too
                    def amount_ok(r):
                        try:
                            return str(int(round(abs(float(r[3]))))) in text
                        except (TypeError, ValueError):
                            return False
                    # a PDF naming several of our invoice numbers is a list (e.g. the accountant's OSA export), not an invoice:
                    # 2026-10-09 it bound osa.pdf to IKEA IB06464 because that was the only row still missing a PDF
                    if sum(1 for k in known if k in text) >= 3:
                        print(f'LISTA     {acc}/{box} uid {uid} {fn[:40]} -- tobb sorszamot tartalmaz, kihagyva')
                        continue
                    hits = [t for t in todo if n(t[4][2]) in text and has_number(raw_text, t[4][2])
                            and (len(n(t[4][2])) >= 10 or amount_ok(t[4]))]
                    if len(hits) != 1:
                        mkey = f'{key}|{uid}|{fn[:40]}'
                        if len(hits) > 1:
                            stat['nem_egyertelmu'] += 1
                            print(f'TOBB PAR  {acc}/{box} uid {uid} {fn[:40]} -> {", ".join(str(h[4][2]) for h in hits)}')
                            report.append((mkey, f'TOBB SORRA ILLIK ({", ".join(str(h[4][2]) for h in hits)})', acc, box, uid, msg, fn))
                        # the 3-day wait is for the NAV/Billingo lag of a Hungarian invoice; a foreign one (no Hungarian
                        # tax number in the PDF) never gets a row from there, so it goes to Signal on the first run
                        # (2026-10-10: a Supermetrics invoice would have waited 3 days for a row that never comes)
                        elif INVOICE_WORD.search(raw_text) and not any(k in text for k in known) \
                                and ((datetime.date.today() - sent).days >= 3 or not HU_TAX.search(raw_text)) \
                                and sent.isoformat()[:7] >= C.START_MONTH:
                            # an invoice with NO row at all (e.g. a foreign one, not in NAV/Billingo): recorded by the
                            # script itself when every field checks out, else Signal (Zsolt 2026-10-10: general rule)
                            print(f'SOR NELKUL {acc}/{box} uid {uid} {fn[:40]}')
                            queue_or_report(felvesz, report, known, raw_text, data, '.pdf',
                                            (mkey, 'SZAMLA, DE NINCS HOZZA SOR A TABLAKBAN', acc, box, uid, msg, fn))
                        continue
                    ent, ssid, tab, i, r = hits[0]
                    print(f'KOTVE     {ent["key"]:10} {tab} {r[1]} {r[2]} <- {acc}/{box} uid {uid} ({fn[:40]})')
                    stat['kotve'] += 1
                    bound_any = True
                    todo.remove(hits[0])
                    if a.dry:
                        continue
                    name = f'{tab} {str(r[1])[:40]} {r[2]}.pdf'.replace('/', '-')
                    up = gapi.upload(tabla.month_folder(ent, tab), name, data)
                    r[C.COL['Számla']] = f'=HYPERLINK("{up["webViewLink"]}","PDF")'
                    ses.sheets[ssid]['dirty'].add((tab, i))
                    ses.note(ssid, tab, i, f'Számlakép a levélből: {acc} / {box} / uid {uid} ({fn[:60]})')
                # announced by its subject, but no invoice PDF we could read (login link, data in the body, photo):
                # unless the body already names an invoice we have, Signal records it (szamla_felvesz.py)
                if uid in hint and not inv_pdf and not bound_any:
                    plain = n(re.sub(r'<[^>]+>', ' ', body) + ' '.join(t for _, _, t in ptexts))
                    if any(k in plain for k in known):
                        seen.add(uid)
                        continue
                    imgs = [dec(p.get_filename() or '') for p in msg.walk()
                            if p.get_content_maintype() == 'image' and p.get_filename()
                            and len(p.get_payload(decode=True) or b'') > 60_000]
                    why = 'SZAMLA PDF NELKUL' + (f' (kep: {", ".join(imgs)[:80]})' if imgs else ' (link vagy a level torzseben)')
                    print(f'PDF NELKUL {acc}/{box} uid {uid} {dec(msg["Subject"])[:50]}')
                    entry = (f'{key}|{uid}|nopdf', why, acc, box, uid, msg, '')
                    # a PDF that INVOICE_WORD did not recognise (2026-10-10: szamlazz.hu link PDFs) is still read
                    # first: the model + the field checks decide, not one keyword
                    readable = [x for x in ptexts if len(x[2].strip()) >= 80]
                    if readable:
                        fn0, data0, text0 = readable[0]
                        queue_or_report(felvesz, report, known, text0, data0, '.pdf', entry[:6] + (fn0,))
                    elif imgs:                 # a photo of an invoice: the text is in the image, Signal reads it
                        report.append(entry)
                    else:                      # the data is in the body (receipt mails): recorded without a PDF
                        btxt = re.sub(r'[ \t\u00a0]+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'(?is)<(style|script).*?</\1>', ' ', body))))
                        if queue_or_report(felvesz, report, known, f'Subject: {dec(msg["Subject"])}\n{btxt}', None, '', entry):
                            # the mail is NOT the invoice (Zsolt 2026-10-10): the real one is behind the vendor login,
                            # so the row goes in without a document and the document request goes to Signal
                            if re.search(r'@[a-z.]*canva\.com', dec(msg['From'] or ''), re.I):
                                # Canva: Nova downloads it from the logged-in Chrome AS SOON AS the mail arrives
                                # (Zsolt 2026-10-10: 'amikor megjon az e-mail, nem kell a 11-hez ragaszkodni')
                                canva_nova.append(felvesz[-1][0]['sorszam'])
                            else:
                                report.append(entry[:1] + ('SZAMLAKEP KELL A SZOLGALTATO FIOKJABOL (a level csak ertesito)',) + entry[2:])
                    seen.add(uid)
                    continue
                if bound_any or not young or uid in FINAL:
                    seen.add(uid)
            if not a.dry:
                state['seen'][key] = sorted(seen, key=int)[-5000:]
        im.logout()
    ses.flush()
    record(felvesz, report, a.dry)
    state.setdefault('canva_sent', [])
    new_canva = [x for x in canva_nova if x not in state['canva_sent']]
    if new_canva:
        txt = ('[CANVA-SZAMLA, level_figyelo.py] Uj Canva-szamla, a sor felveve szamlakep nelkul: ' + ', '.join(new_canva) +
               '. Futtasd a canva portal-kort (skill szamla-portal-letoltes, sor: canva): Playwright, '
               'canva.com/invoices/<sorszam> letoltes -> portal_pdf_json.py canva -> portal_szinkron.py canva.')
        if a.dry:
            print('NOVA (dry, canva):', new_canva)
        else:
            tok = open('/Users/macmini/marveen/store/.dashboard-token').read().strip()
            req = urllib.request.Request('http://localhost:3420/api/messages', method='POST',
                                         data=json.dumps({'from': 'nova', 'to': 'nova', 'content': txt}).encode(),
                                         headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + tok})
            urllib.request.urlopen(req, timeout=20)
            state['canva_sent'] += new_canva
            print('NOVA: canva atadva:', new_canva)
    # invoice mails that match no row / several rows: to Signal, once per mail+file
    state.setdefault('reported_mail', [])
    newrep = [x for x in report if x[0] not in state['reported_mail']]
    # every run, not only the evening one: an invoice with no row should reach Signal within hours (2026-10-10)
    if newrep:
        lines = [f'{why} | {acc} / {box} / uid {uid} | {dec(m["From"])[:60]} | {dec(m["Subject"])[:80]} | {fn[:60]}'
                 for _, why, acc, box, uid, m, fn in newrep]
        msg = ('[SZAMLA-LEVEL, level_figyelo.py] Ezekben a levelekben szamla van, de gepileg nem kotheto be. '
               'Kerlek nezd meg es vidd fel / add at a szokasos modon (uj sornal a v2 mezokkel). Ok | hol | felado | targy | fajl:\n'
               + '\n'.join(lines))
        if a.dry:
            print('SIGNAL (dry, levelek):', len(newrep))
        else:
            send_signal(msg)
            state['reported_mail'] += [x[0] for x in newrep]
            print('SIGNAL: levelek atadva:', len(newrep))
    # what is still missing goes to Signal, once per row (Zsolt TG 18663)
    if a.signal and todo:
        new, portal = signal_rows(todo, state['signal_sent'])
        for t in portal:
            print(f'PORTAL   {t[0]["key"]} {t[2]} {t[4][1]} {t[4][2]}: {C.portal_only(t[4][1])} -- Signalnak nem megy, Eszter havi taskjaba kerul')
        if new:
            lines = [f'{t[0]["key"]} | {t[2]} | {t[4][1]} | {t[4][2]} | {t[4][3]} {t[4][4]}' for t in new]
            msg = ('[SZAMLAKEP-HIANY, level_figyelo.py] Ezekhez a sorokhoz a gepi levelkereses nem talalt PDF-et '
                   f'(a postafiokokban az utolso {a.napok} nap, mellekletek + Billingo/szamlazz linkek). Kerlek nezd meg oket; '
                   'ha talalsz PDF-et, add at az utjat, linket ne nyiss meg. Ceg | honap | partner | sorszam | osszeg:\n' + '\n'.join(lines))
            if a.dry:
                print('SIGNAL (dry):', len(new), 'sor')
            else:
                send_signal(msg)
                state['signal_sent'] += [t[4][C.COL['Forrás-azonosító']] for t in new]
                print('SIGNAL:', len(new), 'sor atadva')
    if not a.dry:
        json.dump(state, open(STATE + '.tmp', 'w'), indent=0)
        os.replace(STATE + '.tmp', STATE)
    print('OSSZEG:', stat, f'| meg kepnelkuli: {len(todo)}', '| DRY' if a.dry else '')
    return 0


if __name__ == '__main__':
    sys.exit(main())
