#!/usr/bin/env python3
"""Tests for scripts/hooks/pr-uzenetsor-kapu.py.

The queue is a throwaway sqlite file with the live table's shape (agent_messages: id, from_agent,
to_agent, content, status, created_at), never the live database: a gate tested on whatever the queue
holds today goes green or red by the day.
"""
import json, os, sqlite3, subprocess, sys, tempfile, unittest

GATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "pr-uzenetsor-kapu.py")


def run(cmd, db, agent="bit", tool="Bash"):
    p = subprocess.run([sys.executable, GATE, "--agent", agent, "--db", db],
                       input=json.dumps({"tool_name": tool, "tool_input": {"command": cmd}}),
                       capture_output=True, text=True, timeout=20)
    return p.returncode, p.stderr


class PrQueueGateTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.dir.name, "q.db")
        con = sqlite3.connect(self.db)
        con.execute("""CREATE TABLE agent_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, from_agent TEXT NOT NULL,
            to_agent TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', created_at INTEGER NOT NULL)""")
        con.executemany("INSERT INTO agent_messages (id, from_agent, to_agent, content, status, created_at) VALUES (?, ?, ?, ?, ?, 0)", [
            (17240, "nova", "bit", "old, already shown", "delivered"),
            (17241, "nova", "bit", "[ALLJ MEG] do not open the PR", "pending"),
            (17242, "nova", "signal", "for someone else", "pending"),
        ])
        con.commit(); con.close()

    def tearDown(self):
        self.dir.cleanup()

    def test_a_pending_message_stops_pr_create_and_merge(self):
        for cmd in ["gh pr create -R o/r --base dev --title x --body y",
                    "cd /x && gh pr merge 369 -R o/r --squash",
                    "gh api -X PUT repos/o/r/pulls/369/merge -f merge_method=squash"]:
            rc, err = run(cmd, self.db)
            self.assertEqual(rc, 2, cmd)
            self.assertIn("17241", err)
            self.assertIn("ALLJ MEG", err, "the message's start is shown")
            self.assertIn("sor-olvasva:17241", err, "and how to go on after reading it")
            self.assertNotIn("17242", err, "another agent's message is not ours")
            self.assertNotIn("17240", err, "a delivered message was shown in the session: not unread")

    def test_reading_it_lets_the_command_through(self):
        rc, err = run("gh pr merge 369 --squash # sor-olvasva:17241", self.db)
        self.assertEqual((rc, err), (0, ""))

    def test_a_message_newer_than_the_reading_still_stops_it(self):
        con = sqlite3.connect(self.db)
        con.execute("INSERT INTO agent_messages (id, from_agent, to_agent, content, status, created_at) VALUES (17245, 'nova', 'bit', 'newer', 'pending', 0)")
        con.commit(); con.close()
        rc, err = run("gh pr merge 369 --squash # sor-olvasva:17241", self.db)
        self.assertEqual(rc, 2)
        self.assertIn("17245", err)
        self.assertNotIn("17241 from", err, "the one already read is not listed again")

    def test_other_commands_and_tools_pass(self):
        for cmd in ["gh pr view 369", "gh pr list -R o/r", "gh pr checks 369", "git push -u origin x", "echo gh pr merge-ish",
                    "echo 'gh pr merge 5 happens after the review'", "grep -n 'gh pr create' notes.md"]:
            self.assertEqual(run(cmd, self.db)[0], 0, cmd)
        self.assertEqual(run("gh pr merge 1", self.db, tool="Read")[0], 0)

    def test_nothing_pending_passes(self):
        self.assertEqual(run("gh pr create --title x", self.db, agent="copy")[0], 0)

    def test_an_unreadable_queue_blocks(self):
        rc, err = run("gh pr merge 369", os.path.join(self.dir.name, "missing.db"))
        self.assertEqual(rc, 2, "fail closed: a missing queue is not an empty one")
        self.assertIn("could not be read", err)
        self.assertEqual(run("gh pr view 369", os.path.join(self.dir.name, "missing.db"))[0], 0, "only PR commands are gated")


if __name__ == "__main__":
    unittest.main()
