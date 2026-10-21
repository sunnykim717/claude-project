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

## GitHub Pages 로 공개하기

저장소 Settings → Pages 에서 `Deploy from a branch` 를 선택하고 기본 브랜치의 `/ (root)` 를 지정하면
`https://<사용자명>.github.io/<저장소명>/` 주소로 홈페이지가 공개됩니다.

## 바이브 홈페이지 빌더 (`builder/index.html`)

코드를 몰라도 화면에서 내용과 디자인을 고르면 홈페이지 파일이 만들어지는 도구입니다.

1. `builder/index.html` 을 브라우저로 엽니다. (서버나 설치가 필요 없습니다.)
2. 왼쪽 패널에서 제목, 소개, 템플릿, 색상, 글꼴, 섹션, 콘텐츠 목록을 고릅니다. 오른쪽에서 결과를 바로 볼 수 있습니다.
3. `index.html 다운로드` 를 누르면 완성된 파일이 저장됩니다. 이 파일을 GitHub Pages 나 다른 호스팅에 올리면 됩니다.

- 입력 내용은 브라우저에 자동 저장되며, `초기화` 로 되돌릴 수 있습니다.
- 링크는 `http://` 또는 `https://` 로 시작하는 주소만 허용합니다.
