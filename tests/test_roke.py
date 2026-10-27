"""Tests for roke's non-interactive parts. Run: python3 -m unittest discover tests"""

import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

ROKE = Path(__file__).resolve().parent.parent / "roke"
loader = SourceFileLoader("roke", str(ROKE))
spec = importlib.util.spec_from_loader("roke", loader)
roke = importlib.util.module_from_spec(spec)
loader.exec_module(roke)

EXPORT = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<KeePassFile>
  <Meta><RecycleBinUUID>YmluYmluYmluYmluYmluYg==</RecycleBinUUID></Meta>
  <Root><Group>
    <UUID>cm9vdHJvb3Ryb290cm9vdA==</UUID><Name>Passwords</Name>
    <Entry>
      <UUID>dG9wdG9wdG9wdG9wdG9wdA==</UUID>
      <String><Key>Title</Key><Value>Bank</Value></String>
      <String><Key>Password</Key><Value ProtectInMemory="True">new</Value></String>
      <History><Entry>
        <UUID>dG9wdG9wdG9wdG9wdG9wdA==</UUID>
        <String><Key>Title</Key><Value>Bank</Value></String>
        <String><Key>Password</Key><Value>old</Value></String>
      </Entry></History>
    </Entry>
    <Group>
      <UUID>d29ya3dvcmt3b3Jrd29yaw==</UUID><Name>Work</Name>
      <Group>
        <UUID>bWFpbG1haWxtYWlsbWFpbA==</UUID><Name>Mail</Name>
        <Entry>
          <UUID>Z21haWxnbWFpbGdtYWlsZw==</UUID>
          <String><Key>Title</Key><Value>Gmail</Value></String>
          <String><Key>UserName</Key><Value>alice</Value></String>
          <String><Key>URL</Key><Value>https://mail.example.com</Value></String>
          <String><Key>Password</Key><Value>secret</Value></String>
          <String><Key>Notes</Key><Value>line one
line two</Value></String>
        </Entry>
      </Group>
    </Group>
    <Group>
      <UUID>YmluYmluYmluYmluYmluYg==</UUID><Name>Recycle Bin</Name>
      <Entry>
        <UUID>ZGVsZGVsZGVsZGVsZGVsZA==</UUID>
        <String><Key>Title</Key><Value>Deleted</Value></String>
      </Entry>
    </Group>
  </Group></Root>
</KeePassFile>
"""


class TempHome(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        env = {"HOME": str(self.tmp), "XDG_CONFIG_HOME": str(self.tmp / ".config")}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)


class ParseExportTest(unittest.TestCase):
    def test_entries(self):
        entries = {e.title: e for e in roke.parse_export(EXPORT)}
        self.assertEqual(set(entries), {"Bank", "Gmail"})  # no history, no recycle bin
        self.assertEqual((entries["Bank"].path, entries["Bank"].label), ("Bank", "Bank"))
        self.assertEqual(entries["Bank"].password, "new")
        gmail = entries["Gmail"]
        self.assertEqual(gmail.path, "Work > Mail > Gmail")
        self.assertEqual(gmail.label, "Gmail  ·  Work > Mail")
        self.assertEqual((gmail.username, gmail.url), ("alice", "https://mail.example.com"))
        self.assertEqual(gmail.notes, "line one\nline two")


@unittest.skipUnless(shutil.which("keepassxc-cli"), "keepassxc-cli not installed")
class OpenDatabaseTest(TempHome):
    def test_open(self):
        db = self.tmp / "test.kdbx"
        run = lambda *args, stdin: subprocess.run(
            ["keepassxc-cli", *args], input=stdin, text=True, capture_output=True, check=True
        )
        run("db-create", "-p", str(db), stdin="pw\npw\n")
        run("add", "-q", "-u", "bob", "-p", str(db), "Bank", stdin="pw\nsecret\n")

        entries, error = roke.open_database(db, "pw")
        self.assertIsNone(error)
        self.assertEqual([(e.path, e.password) for e in entries], [("Bank", "secret")])

        entries, error = roke.open_database(db, "wrong")
        self.assertIsNone(entries)
        self.assertIn("Invalid credentials", error)


class UsageLogTest(TempHome):
    def setUp(self):
        super().setUp()
        self.db = self.tmp / "test.kdbx"
        self.entry = roke.parse_export(EXPORT)[0]

    def test_round_trip_is_encrypted(self):
        roke.UsageLog(self.db, "pw").touch(self.entry)
        files = list((self.tmp / ".config/roke/cache").iterdir())
        self.assertEqual(len(files), 1)
        self.assertNotIn(self.entry.uuid.encode(), files[0].read_bytes())
        self.assertEqual(files[0].stat().st_mode & 0o777, 0o600)
        self.assertGreater(roke.UsageLog(self.db, "pw").last_used(self.entry), 0)

    def test_password_change_discards(self):
        roke.UsageLog(self.db, "pw").touch(self.entry)
        log = roke.UsageLog(self.db, "changed")
        self.assertEqual(log.times, {})
        self.assertEqual(list((self.tmp / ".config/roke/cache").iterdir()), [])
        log.touch(self.entry)
        self.assertGreater(roke.UsageLog(self.db, "changed").last_used(self.entry), 0)


class StateTest(TempHome):
    def test_push_recent(self):
        for item in ("a", "b", "a", "c"):
            roke.push_recent("list", item)
        self.assertEqual(roke.read_recent("list"), ["c", "a", "b"])

    def test_common_places(self):
        for name in ("Documents", "Downloads", "Stuff"):
            (self.tmp / name).mkdir()
        (self.tmp / ".config").mkdir()
        (self.tmp / ".config/user-dirs.dirs").write_text(
            'XDG_DOCUMENTS_DIR="$HOME/Stuff"\nXDG_MUSIC_DIR="$HOME/"\n'
        )
        self.assertEqual(
            roke.common_places(),
            [self.tmp, self.tmp / "Stuff", self.tmp / "Downloads", Path("/")],
        )

    def test_list_directory(self):
        for name in ("b.kdbx", "A.KDBX", "notes.txt", ".hidden.kdbx"):
            (self.tmp / name).touch()
        for name in ("sub", ".git"):
            (self.tmp / name).mkdir()
        databases, subdirs = roke.list_directory(self.tmp)
        self.assertEqual([p.name for p in databases], ["A.KDBX", "b.kdbx"])
        self.assertEqual([p.name for p in subdirs], ["sub"])


if __name__ == "__main__":
    unittest.main()
