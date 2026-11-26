#!/usr/bin/env python3
"""Tests for scripts/hooks/scheduled-task-register-warn.py (Nova 32038).

Run: python3 scripts/__tests__/scheduled-task-register-warn.test.py

Everything runs on a temp tasks directory and a fake registry CLI (a node script printing a chosen verdict); the real
~/.claude/scheduled-tasks and the install's registry are not touched.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOK = os.path.join(ROOT, 'scripts', 'hooks', 'scheduled-task-register-warn.py')
spec = importlib.util.spec_from_file_location('strw', HOOK)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def payload(tool, ti, ev='PostToolUse'):
    return {'tool_name': tool, 'tool_input': ti, 'hook_event_name': ev}


class Names(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.tasks = os.path.join(self.d, 'scheduled-tasks')
        os.makedirs(os.path.join(self.tasks, 'summa-adat-frissites'))

    def test_path_inside_a_task(self):
        self.assertEqual(m.name_from_path(os.path.join(self.tasks, 'summa-adat-frissites', 'SKILL.md'), self.tasks), 'summa-adat-frissites')
        self.assertEqual(m.name_from_path(os.path.join(self.tasks, 'x-1', 'task-config.json'), self.tasks), 'x-1')

    def test_path_outside_or_the_dir_itself(self):
        self.assertIsNone(m.name_from_path(os.path.join(self.d, 'other', 'SKILL.md'), self.tasks))
        self.assertIsNone(m.name_from_path(self.tasks, self.tasks))
        self.assertIsNone(m.name_from_path(self.tasks + '-masik/a/SKILL.md', self.tasks))  # a sibling with the same prefix
        self.assertIsNone(m.name_from_path('', self.tasks))

    def test_path_through_a_symlink(self):
        link = os.path.join(self.d, 'link')
        os.symlink(self.tasks, link)
        self.assertEqual(m.name_from_path(os.path.join(link, 'summa-adat-frissites', 'SKILL.md'), self.tasks), 'summa-adat-frissites')

    def test_command_names(self):
        self.assertEqual(m.names_from_command("sed -i 's/a/b/' ~/.claude/scheduled-tasks/summa-adat-frissites/SKILL.md"), ['summa-adat-frissites'])
        self.assertEqual(m.names_from_command('cat > "$HOME/.claude/scheduled-tasks/a-1/SKILL.md" <<EOF\nx\nEOF; python3 x.py scheduled-tasks/b_2'), ['a-1', 'b_2'])
        self.assertEqual(m.names_from_command('ls ~/.claude/scheduled-tasks/ && echo scheduled-tasks/a-1/x scheduled-tasks/a-1/y'), ['a-1'])
        self.assertEqual(m.names_from_command('git status'), [])


class Decision(unittest.TestCase):
    def setUp(self):
        self.tasks = os.path.join(tempfile.mkdtemp(), 'scheduled-tasks')
        os.makedirs(os.path.join(self.tasks, 't1'))
        self.edit = payload('Edit', {'file_path': os.path.join(self.tasks, 't1', 'SKILL.md')})

    def v(self, verdict):
        return lambda names: [(verdict, n) for n in names]

    def test_mismatch_warns_with_the_command(self):
        code, text = m.run(self.edit, self.tasks, self.v('hash-mismatch'))
        self.assertEqual(code, 2)
        self.assertIn('t1: hash-mismatch', text)
        self.assertIn('node dist/web/schedule-registry-cli.js register --source hand-edit t1', text)
        self.assertIn('undid nothing', text)

    def test_unregistered_warns(self):
        self.assertEqual(m.run(self.edit, self.tasks, self.v('unregistered'))[0], 2)

    def test_ok_and_not_found_stay_quiet(self):
        self.assertEqual(m.run(self.edit, self.tasks, self.v('ok')), (0, ''))
        self.assertEqual(m.run(self.edit, self.tasks, self.v('not-found')), (0, ''))

    def test_failure_event_too(self):
        p = dict(self.edit, hook_event_name='PostToolUseFailure')
        self.assertEqual(m.run(p, self.tasks, self.v('hash-mismatch'))[0], 2)

    def test_not_the_events_or_tools(self):
        called = []
        spy = lambda names: called.append(names) or [('hash-mismatch', n) for n in names]
        self.assertEqual(m.run(dict(self.edit, hook_event_name='PreToolUse'), self.tasks, spy), (0, ''))
        self.assertEqual(m.run(payload('Read', {'file_path': self.edit['tool_input']['file_path']}), self.tasks, spy), (0, ''))
        self.assertEqual(m.run(payload('Edit', {'file_path': '/tmp/elsewhere/SKILL.md'}), self.tasks, spy), (0, ''))
        self.assertEqual(called, [], 'the registry is not asked when nothing under the tasks directory was named')

    def test_bash_lists_every_bad_task_once(self):
        p = payload('Bash', {'command': 'sed -i x scheduled-tasks/a/SKILL.md scheduled-tasks/b/task-config.json scheduled-tasks/c/SKILL.md'})
        verdicts = {'a': 'hash-mismatch', 'b': 'ok', 'c': 'unregistered'}
        code, text = m.run(p, self.tasks, lambda names: [(verdicts[n], n) for n in names])
        self.assertEqual(code, 2)
        self.assertIn('register --source hand-edit a c\n', text)
        self.assertNotIn('  - b:', text)


class Process(unittest.TestCase):
    """The script as the harness runs it: stdin JSON, exit code, stderr; the registry is a fake node CLI."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.tasks = os.path.join(self.d, 'scheduled-tasks')
        os.makedirs(os.path.join(self.tasks, 't1'))

    def fake_cli(self, verdict):
        p = os.path.join(self.d, 'cli.js')
        with open(p, 'w') as f:
            f.write("const a = process.argv.slice(3); for (const n of a) console.log('%s ' + n); process.exit(%d)\n" % (verdict, 0 if verdict == 'ok' else 1))
        return p

    def call(self, cli, body):
        env = dict(os.environ, SCHEDULED_TASKS_DIR_OVERRIDE=self.tasks, SCHEDULE_REGISTRY_CLI_OVERRIDE=cli)
        env.pop('MARVEEN_DISABLED_HOOKS', None)
        return subprocess.run([sys.executable, '-I', '-S', HOOK], input=body, capture_output=True, text=True, env=env, timeout=30)

    def edit(self):
        return json.dumps(payload('Write', {'file_path': os.path.join(self.tasks, 't1', 'task-config.json')}))

    def test_mismatch_exit_2_and_stderr(self):
        r = self.call(self.fake_cli('hash-mismatch'), self.edit())
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn('t1: hash-mismatch', r.stderr)

    def test_ok_exit_0_silent(self):
        r = self.call(self.fake_cli('ok'), self.edit())
        self.assertEqual((r.returncode, r.stderr), (0, ''))

    def test_fail_open_missing_cli_and_bad_stdin(self):
        r = self.call(os.path.join(self.d, 'nincs.js'), self.edit())  # node exits with an error, no verdict lines
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.call(self.fake_cli('hash-mismatch'), '{not json')
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_switch_off(self):
        env = dict(os.environ, SCHEDULED_TASKS_DIR_OVERRIDE=self.tasks, SCHEDULE_REGISTRY_CLI_OVERRIDE=self.fake_cli('hash-mismatch'),
                   MARVEEN_DISABLED_HOOKS='scheduled-task-register-warn')
        r = subprocess.run([sys.executable, '-I', '-S', HOOK], input=self.edit(), capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
