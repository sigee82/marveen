#!/usr/bin/env python3
"""innosocial-nessa.py: a Pinterest SANDBOX board is refused before anything is sent (Nessa 24989 via Nova 24991).

  python3 scripts/__tests__/innosocial-nessa-sandbox-board.test.py

Post 976 (2026-10-30) failed at publish with "Cannot add non-sandbox pins on sandbox boards. (15)": the sandbox board
371124894233101192 was on the ws-8 TSV and the app's live board list, so every check passed it. The TSV here is a
fixture that STILL holds the sandbox row (the case of the row coming back), next to a real board as the control.
Nothing reaches ssh: the sandbox cases stop in the validation, the control calls pinterest_leg only.
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

ITT = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(ITT), 'innosocial-nessa.py')
SANDBOX, REAL = '371124894233101192', '371124894232617889'

spec = importlib.util.spec_from_file_location('innosocial_nessa', TOOL)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

TMP = tempfile.mkdtemp(prefix='nessa-sandbox-teszt-')
m.BOARDS_TSV = os.path.join(TMP, 'tablak.tsv')
with open(m.BOARDS_TSV, 'w', encoding='utf-8') as f:
    f.write(f'{REAL}\tEgészséges turmixok\n{SANDBOX}\tEgészséges receptek\n')

ok = bad = 0


def check(name, cond, info=''):
    global ok, bad
    if cond:
        ok += 1
        print(f'OK   {name}')
    else:
        bad += 1
        print(f'FAIL {name} {info}')


def run(fn):
    """(exit message or None, stdout)"""
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            fn()
    except SystemExit as e:
        return str(e.code), out.getvalue()
    return None, out.getvalue()


def pin(board):
    return {'board_id': board, 'title': 'Zabkasa', 'link': 'https://21napalatt.hu/recept/zabkasa'}


# new post with a pin leg
err, _ = run(lambda: m.pinterest_leg(1, {'pinterest': pin(SANDBOX)}, None, 'szoveg'))
check('new post: the sandbox board stops', err is not None and 'SANDBOX' in err and SANDBOX in err, err)
# the control: a real board from the same TSV passes
err, out = run(lambda: m.pinterest_leg(1, {'pinterest': pin(REAL)}, None, 'szoveg'))
check('new post: a real board passes', err is None and 'Egészséges turmixok' in out, err)

# add_pinterest_to through main(): stops in validation, before the text gate and ssh
pkg = os.path.join(TMP, 'csomag')
os.makedirs(pkg)
with open(os.path.join(pkg, 'posztok.json'), 'w', encoding='utf-8') as f:
    json.dump({'client_id': m.CLIENT, 'meta_account_id': m.ACCOUNT, 'status': 'pending_review',
               'posts': [{'add_pinterest_to': 976, 'pinterest': pin(SANDBOX)}]}, f)
m.NESSA_DIR = os.path.realpath(TMP) + '/'
m.subprocess.run = lambda *a, **k: (_ for _ in ()).throw(AssertionError('subprocess reached'))
sys.argv = ['innosocial-nessa.py', pkg, '--proba']
err, _ = run(m.main)
check('add_pinterest_to: the sandbox board stops in main()', err is not None and 'SANDBOX' in err, err)

print(f'\n{ok} ok, {bad} fail')
sys.exit(1 if bad else 0)
