# 홈페이지 템플릿 (비영리 단체 기본)

NGO, 사회복지법인, 비영리 법인의 기관 소개와 후원 모금 홈페이지를 기본으로 합니다. 기관 이름, 금액, 계좌, 영수증 발급 방법처럼 사실이 필요한 내용은 직접 확인해서 적어 주세요. 템플릿은 빈칸 안내문만 담고 있습니다.

설정 파일과 콘텐츠 파일을 고치면 홈페이지 파일이 만들어집니다. Node.js 도 AI 도 필요 없고, Python 3 만 있으면 됩니다.

## 폴더 구성

| 폴더 | 무엇을 넣나요? |
| --- | --- |
| `config/site.json` | 기관 이름, 소개 한 줄, 언어 |
| `config/navigation.json` | 메뉴 이름과 주소. 주소는 `/`, `/about`, `/projects`, `/contact` 중 하나 |
| `config/theme.json` | 색(`primaryColor`, `backgroundColor`, `textColor`), 글꼴(`system-ui`, `serif`, `mono`), 모서리(0~32), 여백(`compact`, `normal`, `airy`) |
| `content/home.json` | 첫 화면의 제목, 소개 문구, 버튼 |
| `content/about.json` | 기관소개 글 |
| `content/projects.json` | 주요 사업 목록 (제목, 날짜, 설명, 링크) |
| `content/support.json` | 후원 안내 글, 후원 방법 목록, 영수증·사용 내역 안내 |
| `content/news.json` | 소식 목록 (제목, 날짜, 설명, 링크) |
| `content/contact.json` | 문의 글, 이메일, SNS 링크 |
| `public/images/` | 그림 파일 (아직 페이지에 넣는 설정은 없습니다) |
| `src/components/` | 머리글, 첫 화면, 바닥글의 모양 (`{{이름}}` 자리에 값이 들어갑니다) |
| `src/pages/page.html` | 모든 페이지의 뼈대 |
| `src/styles/site.css` | 페이지 모양 |
| `scripts/validate.py` | 설정과 콘텐츠가 맞는지 검사 |
| `scripts/generate.py` | 검사 후 `dist/` 에 페이지 만들기 |
| `.github/workflows/deploy.yml` | GitHub Pages 에 배포 (새 저장소의 루트로 복사해서 씁니다) |

## 설치 없이 쓰기 (편집기)

`editor/index.html` 파일을 브라우저로 열면 됩니다. 터미널이 필요 없습니다.

- 위쪽 **명령 입력** 칸에 명령을 적고 Enter 를 누릅니다. 아래 버튼을 누르면 명령이 채워집니다.
- 명령 예: `set site.name 민수의 작업실`, `design warm-orange`, `add-project 이름 | 2026-11-03 | 요약 | https://...`, `check`
- 오른쪽 미리보기가 바로 바뀝니다. 페이지별 파일은 **받기** 버튼으로 내려받습니다.
- **설정 저장 (파일)** 로 전체 내용을 파일로 보관하고, **설정 불러오기** 로 다시 엽니다.

편집기 파일은 `scripts/bundle_editor.py` 로 만듭니다. 엔진(`editor/engine.js`)은 Python 생성기와 같은 결과를 내는지 테스트로 확인합니다.

## 사용법 (터미널)

```bash
python scripts/validate.py     # 설정 검사
python scripts/generate.py     # dist/ 에 페이지 만들기
```

`dist/index.html` 을 브라우저로 열어 확인하세요. 고친 뒤에는 두 명령을 다시 실행합니다.

## 주의

- 링크는 `https://` 주소 또는 이 템플릿의 페이지 주소(`/about` 등)만 쓸 수 있습니다.
- 날짜는 `2026-01-15` 형식으로 적습니다.
- 그림은 `public/images/` 에 넣고, 설정에서는 `/images/파일이름` 으로 적습니다.
- 배포하면 `dist/` 의 파일이 공개됩니다. 개인정보는 넣지 마세요.
