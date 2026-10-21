#!/usr/bin/env python3
"""홈페이지 설정 파일로 새 홈페이지를 만들고, 값을 바꾸고, 다시 만드는 명령입니다. AI 와 계정이 필요 없습니다.

사용법:
    python -m homepage_config.cli designs
    python -m homepage_config.cli init --design warm-orange --out 내홈페이지.json
    python -m homepage_config.cli set 내홈페이지.json site.name "민수의 작업실"
    python -m homepage_config.cli check 내홈페이지.json
    python -m homepage_config.cli build 내홈페이지.json --out index.html
    python -m homepage_config.cli to-site-json 내홈페이지.json --out data/site.json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from homepage_config.convert import ConfigError, convert, load_designs
from update_homepage import render_page

KST = timezone(timedelta(hours=9))
TEMPLATE_PATH = Path(__file__).resolve().parent / "template.json"


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"파일을 찾을 수 없습니다: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"JSON 형식이 올바르지 않습니다 ({path}, {e.lineno}줄 {e.colno}칸)")


def _write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _report(warnings):
    if warnings:
        print("참고 (반영되지 않은 설정):")
        for w in warnings:
            print(f"- {w}")


def _convert_or_exit(config):
    try:
        return convert(config)
    except ConfigError as e:
        print("설정을 고쳐 주세요:")
        for err in e.errors:
            print(f"- {err}")
        raise SystemExit(1)


def cmd_designs(args):
    for key, design in load_designs().items():
        print(f"{key:14} {design['label']}  (강조색 {design['primaryColor']}, 배경 {design['backgroundColor']}, 글꼴 {design['font']})")
    return 0


def cmd_init(args):
    out = Path(args.out)
    if out.exists():
        print(f"이미 있는 파일은 덮어쓰지 않습니다: {out}")
        return 1
    config = _read(TEMPLATE_PATH)
    if args.design:
        designs = load_designs()
        if args.design not in designs:
            print(f"디자인은 {', '.join(designs)} 중 하나여야 합니다.")
            return 1
        preset = {k: v for k, v in designs[args.design].items() if k != "label"}
        config["design"] = args.design
        config["theme"] = {"layout": "modern", "responsive": True, **preset}
    _write(out, config)
    print(f"설정 파일을 만들었습니다: {out}")
    return 0


def cmd_check(args):
    site, warnings = _convert_or_exit(_read(args.config))
    print("오류 없음. 설정을 만들 수 있습니다.")
    _report(warnings)
    return 0


def cmd_build(args):
    site, warnings = _convert_or_exit(_read(args.config))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_page(site, datetime.now(KST)), encoding="utf-8")
    print(f"홈페이지를 만들었습니다: {out}")
    _report(warnings)
    return 0


def cmd_to_site_json(args):
    site, warnings = _convert_or_exit(_read(args.config))
    _write(args.out, site)
    print(f"자동화가 읽을 데이터 파일을 만들었습니다: {args.out}")
    _report(warnings)
    return 0


def _dig(config, dotted):
    """'site.name' 같은 경로를 따라갑니다. 중간 묶음이 없으면 새로 만듭니다."""
    keys = dotted.split(".")
    node = config
    for key in keys[:-1]:
        if not isinstance(node.get(key), dict):
            node[key] = {}
        node = node[key]
    return node, keys[-1]


def cmd_set(args):
    config = _read(args.config)
    node, last = _dig(config, args.path)
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value
    node[last] = value
    # 바꾼 뒤에도 설정이 맞는지 확인하고, 맞을 때만 저장합니다.
    _, warnings = _convert_or_exit(config)
    _write(args.config, config)
    print(f"{args.path} 을(를) 바꾸고 저장했습니다: {value!r}")
    _report(warnings)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="homepage_config", description="홈페이지 설정으로 홈페이지 만들기")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("designs", help="기본 디자인 목록 보기").set_defaults(func=cmd_designs)

    p = sub.add_parser("init", help="설정 파일 새로 만들기")
    p.add_argument("--design", help="기본 디자인 이름 (designs 명령으로 확인)")
    p.add_argument("--out", default="내홈페이지.json", help="만들 설정 파일 경로")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("check", help="설정이 맞는지 확인하기")
    p.add_argument("config")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("build", help="설정으로 index.html 만들기")
    p.add_argument("config")
    p.add_argument("--out", default="index.html")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("to-site-json", help="저장소 자동화가 읽는 data/site.json 만들기")
    p.add_argument("config")
    p.add_argument("--out", default="data/site.json")
    p.set_defaults(func=cmd_to_site_json)

    p = sub.add_parser("set", help="설정 값 바꾸기. 예: set 설정.json site.name \"새 이름\"")
    p.add_argument("config")
    p.add_argument("path", help="바꿀 항목 경로. 예: site.name, theme.primaryColor")
    p.add_argument("value", help="새 값. 숫자, true/false 는 그대로, 글자는 그냥 적습니다.")
    p.set_defaults(func=cmd_set)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
