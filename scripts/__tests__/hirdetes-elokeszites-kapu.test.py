#!/usr/bin/env python3
"""Tests for scripts/hooks/hirdetes-elokeszites-kapu.py.

Every case runs on a throwaway skills folder and a throwaway transcript, never on Copy's live ones: a gate
tested on whatever the live session holds goes green or red by the day.
"""
import json, os, subprocess, sys, tempfile, unittest

GATE = os.environ.get("HIRDETES_KAPU_GATE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "hirdetes-elokeszites-kapu.py")
AD_MSG = ("curl -s -X POST http://localhost:3420/api/messages -H 'Content-Type: application/json' --data-binary @- <<'JSON'\n"
          '{"from":"copy","to":"nova","content":"VIP Meta-hirdetés v4: a három elsődleges szöveg kész."}\nJSON')
PLAIN_MSG = ("curl -s -X POST http://localhost:3420/api/messages --data-binary @- <<'JSON'\n"
             '{"from":"copy","to":"nova","content":"A hírlevél tárgysora kész."}\nJSON')


def tool_use(name, inp):
    return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "t", "name": name, "input": inp}]}}


class AdGateTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = self.dir.name
        self.skills = os.path.join(d, "skills")
        self.mintak = os.path.join(self.skills, "ad-copy", "references", "magyar-mintak")
        os.makedirs(os.path.join(self.mintak, "_nyers"))
        os.makedirs(os.path.join(self.skills, "copywriter-core"))
        self.files = [os.path.join(self.mintak, n) for n in ("00-INDEX.md", "01-masok.md")]
        self.mercek = os.path.join(self.skills, "ad-copy", "references", "zsolt-hirdetes-mercek.md")
        for f in self.files + [self.mercek, os.path.join(self.mintak, "_nyers", "raw.md"),
                               os.path.join(self.skills, "ad-copy", "SKILL.md"), os.path.join(self.skills, "copywriter-core", "SKILL.md")]:
            with open(f, "w") as fh:
                fh.write("x")
        self.transcript = os.path.join(d, "t.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def session(self, events):
        with open(self.transcript, "w") as fh:
            fh.write(json.dumps({"type": "user", "message": {"role": "user", "content": "hello"}}) + "\n")
            for e in events:
                fh.write(json.dumps(e) + "\n")

    def full_prep(self):
        return [tool_use("Skill", {"skill": "copywriter-core"}), tool_use("Skill", {"skill": "ad-copy"})] + \
               [tool_use("Read", {"file_path": f}) for f in self.files + [self.mercek]]

    def run_gate(self, tool, inp, transcript=None, cwd=None):
        p = subprocess.run([sys.executable, GATE, "--skills-dir", self.skills],
                           input=json.dumps({"tool_name": tool, "tool_input": inp, "cwd": cwd or self.dir.name,
                                             "transcript_path": self.transcript if transcript is None else transcript}),
                           capture_output=True, text=True, timeout=20)
        return p.returncode, p.stderr

    def test_ad_message_without_prep_is_blocked_and_every_step_named(self):
        self.session([])
        rc, err = self.run_gate("Bash", {"command": AD_MSG})
        self.assertEqual(rc, 2)
        for s in ("copywriter-core", "ad-copy skill", "00-INDEX.md", "01-masok.md", "zsolt-hirdetes-mercek.md"):
            self.assertIn(s, err)
        self.assertNotIn("raw.md", err)  # only the top-level files of magyar-mintak

    def test_full_prep_lets_it_through(self):
        self.session(self.full_prep())
        self.assertEqual(self.run_gate("Bash", {"command": AD_MSG})[0], 0)

    def test_one_unread_file_is_named_alone(self):
        self.session(self.full_prep()[:-1])  # the yardstick file not read
        rc, err = self.run_gate("Bash", {"command": AD_MSG})
        self.assertEqual(rc, 2)
        self.assertIn("zsolt-hirdetes-mercek.md", err)
        self.assertNotIn("00-INDEX.md", err)
        self.assertNotIn("skill (Skill", err)

    def test_one_skill_missing_is_named(self):
        self.session([e for e in self.full_prep() if e["message"]["content"][0]["input"].get("skill") != "copywriter-core"])
        rc, err = self.run_gate("Bash", {"command": AD_MSG})
        self.assertEqual(rc, 2)
        self.assertIn("load the copywriter-core skill", err)
        self.assertNotIn("load the ad-copy skill", err)

    def test_skill_md_read_or_typed_command_counts_as_loading(self):
        ev = [tool_use("Read", {"file_path": os.path.join(self.skills, "copywriter-core", "SKILL.md")}),
              {"type": "user", "message": {"role": "user", "content": "<command-name>/ad-copy</command-name>"}}]
        self.session(ev + self.full_prep()[2:])
        self.assertEqual(self.run_gate("Bash", {"command": AD_MSG})[0], 0)

    def test_bash_cat_counts_but_a_write_naming_the_file_does_not(self):
        prep = self.full_prep()[:2]
        cat = tool_use("Bash", {"command": "cat " + " ".join(self.files + [self.mercek])})
        self.session(prep + [cat])
        self.assertEqual(self.run_gate("Bash", {"command": AD_MSG})[0], 0)
        writes = tool_use("Bash", {"command": f"cd {self.mintak} && python3 - <<'PY'\nopen('00-INDEX.md','w').write('y')\nPY\n"
                                              f"sed -i '' s/a/b/ {self.mercek}"})
        self.session(prep + [writes] + [tool_use("Read", {"file_path": self.files[1]})])
        rc, err = self.run_gate("Bash", {"command": AD_MSG})
        self.assertEqual(rc, 2)
        self.assertIn("00-INDEX.md", err)
        self.assertIn("zsolt-hirdetes-mercek.md", err)

    def test_message_text_from_a_data_file_is_read(self):
        self.session([])
        f = os.path.join(self.dir.name, "msg.json")
        open(f, "w").write(json.dumps({"from": "copy", "to": "pixel", "content": "KREATIV-SZOVEG: primary text v2"}))
        self.assertEqual(self.run_gate("Bash", {"command": f"curl -s -X PUT http://localhost:3420/api/messages/9 --data-binary @{f}"})[0], 2)
        open(f, "w").write(json.dumps({"from": "copy", "to": "nova", "content": "A hírlevél kész."}))
        self.assertEqual(self.run_gate("Bash", {"command": f"curl -s -X PUT http://localhost:3420/api/messages/9 --data-binary @{f}"})[0], 0)

    def test_not_an_ad_or_not_a_message_passes_without_looking(self):
        self.assertEqual(self.run_gate("Bash", {"command": PLAIN_MSG}, transcript="/nonexistent")[0], 0)
        self.assertEqual(self.run_gate("Bash", {"command": "grep -r hirdetés workspace/"}, transcript="/nonexistent")[0], 0)
        # reading a message back (a GET) is not handing anything in, even if the command mentions an ad
        self.assertEqual(self.run_gate("Bash", {"command": "curl -s http://localhost:3420/api/messages/25390 | grep -c hirdetés"}, transcript="/nonexistent")[0], 0)

    def test_files_in_an_ad_folder_are_gated_but_skill_references_are_not(self):
        self.session([])
        self.assertEqual(self.run_gate("Write", {"file_path": "/Users/macmini/marveen/agents/copy/workspace/vip-meta-20261102/v4.md", "content": "x"})[0], 2)
        self.assertEqual(self.run_gate("Edit", {"file_path": "/Users/macmini/marveen/agents/copy/atadas/hirdetes-kviz/a.md"})[0], 2)
        self.assertEqual(self.run_gate("Write", {"file_path": "/Users/macmini/marveen/agents/copy/.claude/skills/ad-copy/references/zsolt-hirdetes-mercek.md"})[0], 0)
        self.assertEqual(self.run_gate("Write", {"file_path": "/Users/macmini/marveen/agents/copy/workspace/hirlevel-w45/a.md"})[0], 0)

    def test_drive_write_about_an_ad_is_gated(self):
        self.session([])
        self.assertEqual(self.run_gate("mcp__google-drive__createGoogleDoc", {"title": "VIP Meta-hirdetés v4"})[0], 2)
        self.assertEqual(self.run_gate("mcp__google-drive__createGoogleDoc", {"title": "Hírlevél w45"})[0], 0)
        self.assertEqual(self.run_gate("mcp__google-drive__readGoogleDoc", {"title": "VIP Meta-hirdetés v4"})[0], 0)

    def test_fail_closed(self):
        rc, err = self.run_gate("Bash", {"command": AD_MSG}, transcript=os.path.join(self.dir.name, "missing.jsonl"))
        self.assertEqual(rc, 2)
        self.assertIn("could not be read", err)
        self.session(self.full_prep())
        os.rename(self.mercek, self.mercek + ".gone")
        rc, err = self.run_gate("Bash", {"command": AD_MSG})
        self.assertEqual(rc, 2)
        self.assertIn("missing", err)


if __name__ == "__main__":
    unittest.main()
