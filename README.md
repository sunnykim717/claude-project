# 홈페이지 자동 업데이트

`data/site.json` 데이터를 읽어 `index.html` 을 자동으로 생성하고,
GitHub Actions 가 매일 정해진 시간에 이를 갱신해 커밋합니다. 외부 라이브러리 없이 Python 표준 라이브러리만 사용합니다.

## 구성

| 파일 | 역할 |
| --- | --- |
| `data/site.json` | 홈페이지 내용(제목, 소개, 소식 목록)을 담는 데이터 파일 |
| `update_homepage.py` | JSON 을 읽어 `index.html` 을 생성 |
| `index.html` | 생성된 홈페이지 (직접 수정하지 마세요) |
| `.github/workflows/update-homepage.yml` | 매일 09:00 KST 에 테스트 → 생성 → 커밋 |
| `tests/test_update_homepage.py` | 생성기 단위 테스트 |

## 사용법

### 1. 내용 수정

`data/site.json` 을 편집합니다.

```json
{
  "title": "나의 홈페이지",
  "subtitle": "짧은 소개 문구",
  "lang": "ko",
  "items": [
    {
      "title": "소식 제목",
      "date": "2026-10-21",
      "summary": "요약 (선택)",
      "url": "https://example.com (선택)"
    }
  ]
}
```

- `title` 은 필수이며, 각 `items` 항목에도 `title` 이 필요합니다.
- `items` 는 `date` 기준 최신순으로 자동 정렬됩니다.
- 입력값은 HTML 이스케이프 처리되어 안전하게 출력됩니다.

### 2. 로컬에서 생성

```bash
python update_homepage.py
python -m unittest discover -s tests
```

### 3. 자동 업데이트

- **매일 자동 실행**: `.github/workflows/update-homepage.yml` 의 `cron` 값으로 주기를 바꿀 수 있습니다 (UTC 기준).
- **즉시 실행**: GitHub 저장소의 Actions 탭에서 `Update homepage` 를 `Run workflow` 로 실행합니다.
- **데이터 변경 시**: `data/site.json` 이나 `update_homepage.py` 를 push 하면 자동으로 다시 생성됩니다.

변경 사항이 없으면 커밋하지 않습니다.

## 바이브 코딩으로 내용 수정 (클라우드 세션 우선)

자연어로 요청하면 Claude Code 클라우드 세션이 `data/site.json` 만 수정합니다. API 키는 필요 없습니다.

1. Claude Code 클라우드 세션을 이 저장소에 연결합니다. 세션은 [`docs/content-guide.md`](docs/content-guide.md)의 작성 규칙을 따릅니다.
2. 요청을 말합니다. 예: "프로젝트에 2026-10-21 자 '빌더 공개' 항목 추가하고 제목을 '민수의 작업실'로 바꿔 줘"
   - 문장 초안도 부탁할 수 있습니다. 예: "프로젝트 설명을 세 문장으로 다듬어 줘"
   - 날짜나 링크처럼 사실인 정보는 요청에 직접 적어 주세요. 세션은 지어내지 않습니다.
3. 세션은 `data/site.json` 만 고치고, `python -m unittest discover -s tests` 와 `python update_homepage.py` 로 확인한 뒤 push 합니다.
4. push 가 `data/site.json` 을 건드리면 워크플로가 검증, 생성, 커밋을 자동으로 처리합니다.

검증 실패 시(예: `javascript:` 링크, 잘못된 날짜 형식) 생성기가 오류를 내고 커밋하지 않습니다.

## GitHub Pages 로 공개하기

저장소 Settings → Pages 에서 `Deploy from a branch` 를 선택하고 기본 브랜치의 `/ (root)` 를 지정하면
`https://<사용자명>.github.io/<저장소명>/` 주소로 홈페이지가 공개됩니다.

## 바이브 홈페이지 빌더 (`builder/index.html`)

코드를 몰라도 화면에서 내용과 디자인을 고르면 홈페이지 파일이 만들어지는 도구입니다.

1. `builder/index.html` 을 브라우저로 엽니다. (서버나 설치가 필요 없습니다.)
2. 왼쪽 패널에서 제목, 소개, 템플릿, 색상, 글꼴, 섹션, 콘텐츠 목록을 고릅니다. 오른쪽에서 결과를 바로 볼 수 있습니다.
3. `index.html 다운로드` 를 누르면 완성된 파일이 저장됩니다. 이 파일을 GitHub Pages 나 다른 호스팅에 올리면 됩니다.
4. 오른쪽 `AI 요청용 상세 명세서` 를 `명세서 복사` 하면, 지금 설정과 똑같은 홈페이지를 AI에게 요청할 때 쓸 수 있는 명세가 만들어집니다.

### 검수 규칙

- 제목 60자, 검색용 설명 160자 권장
- 글자색과 배경색 대비 4.5:1 이상 (WCAG AA), 버튼 글자와 버튼 배경 대비 4.5:1 이상
- 모든 링크는 `https://` 로 시작해야 하며, `javascript:` 같은 주소는 막힙니다.
- 날짜는 `YYYY-MM-DD` 형식이어야 합니다.

### 명세 파일

`명세(JSON) 저장` 으로 내용을 파일로 보관하고, `명세 불러오기` 로 다시 열 수 있습니다.

- 입력 내용은 브라우저에 자동 저장되며, `초기화` 로 되돌릴 수 있습니다.
- 링크는 `http://` 또는 `https://` 로 시작하는 주소만 허용합니다.
