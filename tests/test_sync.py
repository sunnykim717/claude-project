"""승인된 GitHub 보내기(scripts/sync.py)를 임시 저장소에서 확인합니다. 실제 GitHub 에는 아무것도 보내지 않습니다."""

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "website-template" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import sync  # noqa: E402

APPROVED_URL = "https://github.com/sunnykim717/claude-project.git"
BRANCH = "claude/test-sync"


def git(cwd, *args):
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8", check=True)
    return result.stdout.strip()


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.remote = self.tmp / "remote.git"
        self.repo = self.tmp / "repo"
        self.site = self.repo / "site"
        subprocess.run(["git", "init", "-q", "--bare", str(self.remote)], check=True)
        subprocess.run(["git", "init", "-q", "-b", BRANCH, str(self.repo)], check=True)
        git(self.repo, "config", "user.name", "tester")
        git(self.repo, "config", "user.email", "tester@example.invalid")
        git(self.repo, "remote", "add", "origin", APPROVED_URL)
        # 승인된 GitHub 주소를 임시 원격으로 바꿔 보내기를 흉내 냅니다. origin 자체는 그대로 둡니다.
        git(self.repo, "config", f"url.{self.remote}.insteadOf", APPROVED_URL)
        (self.site / "config").mkdir(parents=True)
        (self.site / "content").mkdir()
        (self.site / "config" / "sync.json").write_text(json.dumps({"repo": "sunnykim717/claude-project", "branch": BRANCH}), encoding="utf-8")
        (self.site / "content" / "news.json").write_text('{"title": "소식"}\n', encoding="utf-8")
        (self.repo / "outside.txt").write_text("repo 의 다른 파일\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "start")
        git(self.repo, "push", "-q", "-u", "origin", BRANCH)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def remote_count(self):
        return int(subprocess.run(["git", "--git-dir", str(self.remote), "rev-list", "--count", BRANCH],
                                  capture_output=True, text=True, check=True).stdout.strip())

    def run_quiet(self, **kwargs):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sync.run_sync(self.site, **kwargs)
        return code, out.getvalue()

    def test_dry_run_sends_nothing(self):
        (self.site / "content" / "news.json").write_text('{"title": "새 소식"}\n', encoding="utf-8")
        before = self.remote_count()
        code, out = self.run_quiet(push=False)
        self.assertEqual(code, 0)
        self.assertIn("아직 아무것도 보내지 않았습니다", out)
        self.assertEqual(self.remote_count(), before)
        self.assertIn("news.json", git(self.repo, "status", "--porcelain"))

    def test_push_commits_only_the_site_folder(self):
        (self.site / "content" / "news.json").write_text('{"title": "새 소식"}\n', encoding="utf-8")
        (self.repo / "outside.txt").write_text("바뀐 다른 파일\n", encoding="utf-8")
        before = self.remote_count()
        code, out = self.run_quiet(push=True)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.remote_count(), before + 1)
        changed = subprocess.run(["git", "--git-dir", str(self.remote), "show", "--name-only", "--format=", BRANCH],
                                 capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(changed, ["site/content/news.json"])
        self.assertIn("outside.txt", git(self.repo, "status", "--porcelain"))

    def test_no_changes_is_not_an_error(self):
        code, out = self.run_quiet(push=True)
        self.assertEqual(code, 0)
        self.assertIn("보낼 변경이 없습니다", out)

    def test_refuses_other_repository(self):
        git(self.repo, "remote", "set-url", "origin", "https://github.com/someone/else.git")
        with self.assertRaisesRegex(sync.SyncError, "승인된 저장소"):
            self.run_quiet(push=False)

    def test_refuses_other_branch(self):
        git(self.repo, "checkout", "-q", "-b", "claude/other")
        with self.assertRaisesRegex(sync.SyncError, "브랜치"):
            self.run_quiet(push=False)

    def test_refuses_default_branch_in_config(self):
        (self.site / "config" / "sync.json").write_text(json.dumps({"repo": "sunnykim717/claude-project", "branch": "main"}), encoding="utf-8")
        with self.assertRaisesRegex(sync.SyncError, "기본 브랜치|main"):
            self.run_quiet(push=True)

    def test_refuses_when_remote_has_newer_commits(self):
        other = self.tmp / "other"
        subprocess.run(["git", "clone", "-q", "-b", BRANCH, str(self.remote), str(other)], check=True)
        git(other, "config", "user.name", "other")
        git(other, "config", "user.email", "other@example.invalid")
        (other / "note.txt").write_text("다른 사람이 먼저 올린 변경\n", encoding="utf-8")
        git(other, "add", "-A")
        git(other, "commit", "-q", "-m", "other")
        git(other, "push", "-q", "origin", BRANCH)
        (self.site / "content" / "news.json").write_text('{"title": "내 변경"}\n', encoding="utf-8")
        before = self.remote_count()
        with self.assertRaisesRegex(sync.SyncError, "새 변경"):
            self.run_quiet(push=True)
        self.assertEqual(self.remote_count(), before)

    def test_missing_config_is_explained(self):
        (self.site / "config" / "sync.json").unlink()
        with self.assertRaisesRegex(sync.SyncError, "sync.json"):
            self.run_quiet(push=False)


if __name__ == "__main__":
    unittest.main()
