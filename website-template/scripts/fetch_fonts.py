#!/usr/bin/env python3
"""개발 단계에서만 실행합니다: fonts/registry.json 에 적힌 글꼴 파일을 npm 패키지에서 받아 fonts/files 에 둡니다.

일반 사용자의 생성·빌드 단계는 이 스크립트를 쓰지 않습니다. 받은 파일의 sha256 을 fonts/checksums.json 에 기록합니다.
사용법: python scripts/fetch_fonts.py
"""

import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"


def npm_pack(package, version, dest):
    """npm pack 으로 패키지 한 개를 받습니다. 인증 정보는 쓰지 않습니다."""
    result = subprocess.run(["npm", "pack", f"{package}@{version}", "--silent"], cwd=dest,
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"npm pack {package}@{version} 실패: {result.stderr.strip()[:200]}")
    archive = Path(result.stdout.strip().splitlines()[-1])
    return dest / archive.name


def safe_extract(archive, dest):
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            target = (dest / member.name).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise RuntimeError("압축 파일 경로가 이상합니다")
        tar.extractall(dest, filter="data")


def main():
    registry = json.loads((FONTS / "registry.json").read_text(encoding="utf-8"))
    checksums = {}
    files_dir = FONTS / "files"
    licenses_dir = FONTS / "licenses"
    if files_dir.exists():
        shutil.rmtree(files_dir)
    files_dir.mkdir(parents=True)
    licenses_dir.mkdir(parents=True, exist_ok=True)
    for font in registry["fonts"]:
        source = font["source"]
        if source["type"] != "npm":
            continue
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive = npm_pack(source["package"], source["version"], tmp_path)
            extract = tmp_path / "x"
            extract.mkdir()
            safe_extract(archive, extract)
            for item in font["files"]:
                src = extract / item["from"]
                if not src.exists():
                    raise RuntimeError(f"{font['id']}: 파일이 없습니다 ({item['from']})")
                name = f"{font['id']}-{item['weight']}.woff2"
                shutil.copyfile(src, files_dir / name)
                checksums[f"fonts/files/{name}"] = hashlib.sha256(src.read_bytes()).hexdigest()
            license_src = next(extract.glob("**/LICENSE*"), None)
            if license_src is not None:
                shutil.copyfile(license_src, licenses_dir / f"{font['id']}-LICENSE.txt")
        print(f"받았습니다: {font['label']} {source['version']}")
    (FONTS / "checksums.json").write_text(json.dumps(checksums, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"파일 {len(checksums)}개와 체크섬을 기록했습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
