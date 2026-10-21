"""승인된 GitHub 저장소·브랜치로 홈페이지 변경을 보냅니다.

- 실행할 때만 동작합니다. 기본은 보내기 전 확인(dry run)이고, `--push` 를 붙여야 커밋하고 올립니다.
- config/sync.json 에 적은 저장소(repo)와 브랜치(branch)만 씁니다. 다른 곳이면 멈춥니다.
- main, master 같은 기본 브랜치는 공개 배포로 이어지므로 보내지 않습니다.
- 원격 브랜치에 내 기록에 없는 새 커밋이 있으면(충돌 위험) 멈춥니다. 강제 push 는 하지 않습니다.
- 커밋은 이 폴더(홈페이지) 안의 변경만 담습니다. 저장소의 다른 파일은 건드리지 않습니다.
- 인증 정보는 저장하거나 출력하지 않습니다. git 이 이미 가진 로그인을 그대로 씁니다.
"""

import json
import re
import subprocess
from pathlib import Path

PROTECTED_BRANCHES = ("main", "master")
REPO_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")
REMOTE_PATTERN = re.compile(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$")
COMMIT_MESSAGE = "홈페이지 내용을 고쳤습니다 (site_tool sync)"


class SyncError(Exception):
    """보내기를 멈춰야 할 때 사용자에게 보여 줄 이유."""


def _run(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8")


def _git(root, *args):
    result = _run(root, *args)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SyncError(f"git {args[0]} 에 실패했습니다: {detail}")
    return result.stdout.strip()


def load_config(root):
    path = Path(root) / "config" / "sync.json"
    if not path.exists():
        raise SyncError("config/sync.json 이 없습니다. 보낼 저장소(repo)와 브랜치(branch)를 먼저 적어 주세요.")
    data = json.loads(path.read_text(encoding="utf-8"))
    repo, branch = str(data.get("repo", "")), str(data.get("branch", ""))
    if not REPO_PATTERN.match(repo):
        raise SyncError("config/sync.json 의 repo 는 owner/repo 형식이어야 합니다.")
    if not branch:
        raise SyncError("config/sync.json 의 branch 를 적어 주세요.")
    if branch in PROTECTED_BRANCHES:
        raise SyncError(f"{branch} 브랜치에는 보내지 않습니다. 작업용 브랜치를 쓰세요.")
    return repo, branch


def check_remote(root, repo):
    # insteadOf 로 바뀐 주소가 아니라, 저장소에 적힌 원래 주소로 확인합니다.
    url = _git(root, "config", "--get", "remote.origin.url")
    match = REMOTE_PATTERN.search(url)
    if not match or match.group(1) != repo:
        raise SyncError(f"origin 이 승인된 저장소({repo})가 아닙니다. 현재: {url}")


def check_branch(root, branch):
    current = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if current != branch:
        raise SyncError(f"현재 브랜치({current})가 승인된 브랜치({branch})와 다릅니다. git checkout {branch} 후 다시 실행하세요.")


def check_not_behind(root, branch):
    """원격 브랜치에 내 기록에 없는 커밋이 있으면 충돌 위험이므로 멈춥니다."""
    listed = _git(root, "ls-remote", "--heads", "origin", branch)
    if not listed:
        return  # 원격에 아직 없는 새 브랜치
    _git(root, "fetch", "origin", branch)
    ahead = _run(root, "merge-base", "--is-ancestor", "FETCH_HEAD", "HEAD")
    if ahead.returncode != 0:
        raise SyncError("원격 브랜치에 내 기록에 없는 새 변경이 있습니다. 먼저 받아서 합친 뒤 다시 실행하세요. 강제 보내기는 하지 않습니다.")


def run_sync(root, push=False):
    """보내기를 실행합니다. 성공하면 0, 아무것도 보낼 게 없으면 0, 막히면 SyncError 를 던집니다."""
    repo, branch = load_config(root)
    check_remote(root, repo)
    check_branch(root, branch)
    changes = _git(root, "status", "--porcelain", "--", ".").splitlines()
    print(f"보낼 곳: {repo} 의 {branch} 브랜치")
    if not changes:
        print("보낼 변경이 없습니다.")
        return 0
    print("바뀐 파일:")
    for line in changes:
        print(f"  {line}")
    check_not_behind(root, branch)
    if not push:
        print("아직 아무것도 보내지 않았습니다. 보내려면 sync --push 를 실행하세요.")
        return 0
    _git(root, "add", "--", ".")
    _git(root, "commit", "-m", COMMIT_MESSAGE, "--", ".")
    _git(root, "push", "-u", "origin", branch)
    print(f"보냈습니다: {repo} 의 {branch} 브랜치")
    return 0
