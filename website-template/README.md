# 홈페이지 템플릿 (비영리 단체 기본)

NGO, 사회복지법인, 비영리 법인의 기관 소개와 후원 모금 홈페이지를 기본으로 합니다. 기관 이름, 금액, 계좌, 영수증 발급 방법처럼 사실이 필요한 내용은 직접 확인해서 적어 주세요. 템플릿은 빈칸 안내문만 담고 있습니다.

설정 파일과 콘텐츠 파일을 고치면 홈페이지 파일이 만들어집니다. Node.js 도 AI 도 필요 없고, Python 3 만 있으면 됩니다.

## 처음 시작하기 (5분)

둘 중 하나를 고르면 됩니다.

**A. 브라우저에서 (터미널 없이)**

> 편집기 열기: [편집기 파일 보기](https://github.com/sunnykim717/claude-project/blob/claude/funny-franklin-mknfpi/website-template/editor/index.html) — 이 페이지에서 **Raw** 를 누르거나 파일을 내려받아 `index.html` 로 저장한 뒤 브라우저로 여세요. 저장소를 합치면 주소의 `claude/funny-franklin-mknfpi` 부분이 `main` 으로 바뀝니다.

1. `editor/index.html` 을 브라우저(크롬, 엣지 등)로 엽니다.
2. 위쪽 명령 칸에 적고 Enter 를 누릅니다. 예: `set site.name 희망 나눔 복지재단`
3. 오른쪽 미리보기에서 확인하고, **프로젝트 내려받기 (zip)** 을 누릅니다.
4. 받은 zip 을 풀고 아래 **배포하기** 를 따릅니다.

**B. 터미널에서 (Python 3 만 있으면 됩니다)**

```bash
python scripts/site_tool.py new ../내홈페이지 --name 희망 나눔 복지재단 --design warm-orange
cd ../내홈페이지
python scripts/site_tool.py set home.hero.title 함께 걸어가는 이웃
python scripts/site_tool.py check
python scripts/site_tool.py build --out dist
```

- `designs` 명령으로 디자인 목록을 볼 수 있습니다.
- `set` 뒤의 값은 따옴표 없이 여러 단어를 써도 됩니다.
- `check` 는 틀린 곳을 알려 줍니다. 메시지에 나온 파일을 고치고 다시 실행하세요.

**배포하기 (GitHub Pages)**

1. 이 폴더를 새 GitHub 저장소의 최상위에 올립니다.
2. 저장소 **Settings → Pages** 에서 Source 를 **GitHub Actions** 로 고릅니다.
3. `.github/workflows/deploy.yml` 이 `main` 에 올라가면 자동으로 배포됩니다.

> 배포 전에 `content/` 의 빈칸 안내문을 실제 내용으로 바꾸세요. 기관 정보, 금액, 계좌, 영수증 안내는 직접 확인해서 적어야 합니다.

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
| `content/greetings.json`, `history.json`, `events.json`, `stories.json`, `library.json`, `faq.json`, `location.json` | 추가 페이지 (제목, 본문, 목록) |
| `config/custom.css` | 직접 쓰는 CSS |
| `content/transparency.json` | 투명성·재무 공개: 사업·재무 자료, 사업비 구성, 외부 확인 경로 |
| `content/volunteer.json` | 자원봉사 안내: 활동 종류, 신청 방법 |
| `content/privacy.json` | 개인정보 처리방침 (바닥글에 자동으로 링크됩니다) |
| `content/contact.json` | 문의 글, 이메일, SNS 링크 |
| `public/images/` | 사진 파일. 편집기 또는 `image` 설정으로 페이지에 넣습니다 |
| `src/components/` | 머리글, 첫 화면, 바닥글의 모양 (`{{이름}}` 자리에 값이 들어갑니다) |
| `src/pages/page.html` | 모든 페이지의 뼈대 |
| `src/styles/site.css` | 페이지 모양 |
| `scripts/validate.py` | 설정과 콘텐츠가 맞는지 검사 |
| `scripts/generate.py` | 검사 후 `dist/` 에 페이지 만들기 |
| `.github/workflows/deploy.yml` | GitHub Pages 에 배포 (새 저장소의 루트로 복사해서 씁니다) |

## 꾸미기 선택지

| 무엇을 | 고를 수 있는 것 | 어디에 적나요? |
| --- | --- | --- |
| 디자인 한 번에 | 25가지 (`designs` 명령으로 목록 확인) | `design 이름` 또는 `new --design` |
| 글꼴 | system-ui, sans, myeongjo, rounded, humanist, modern-latin, serif, classic-latin, mono | `theme.font` |
| 여백 | tight, compact, normal, airy, spacious | `theme.spacing` |
| 배치 | classic, modern, card, minimal, wide, bold | `theme.layout` |
| 메뉴 모양 | row(가로), center(가운데), buttons(버튼), stack(세로) | `theme.menu` |
| 배경 사진 | 사진 한 장 (배경색 위에 얇은 막) | `theme.backgroundImage` |
| 로고 | 사진 한 장 (머리글 이름 앞) | `site.logo` |
| 페이지 사진 | 대표 사진 한 장 + 갤러리 최대 12장 | 페이지의 `image`, `gallery` |
| 페이지 | 기본 8개 + 추가 7개 (인사말, 연혁, 행사·캠페인, 활동 이야기, 자료실, 자주 묻는 질문, 오시는 길) | 메뉴에 `add-menu` |
| 첫 화면 칸 순서 | intro, projects, news 중 골라 순서대로 | `home.sections` |
| 직접 쓰는 CSS | 모든 페이지 맨 뒤에 붙음 | `config/custom.css` |

- 메뉴 추가: `add-menu 오시는 길 | /location`, 삭제: `remove-menu 번호` (편집기와 `site_tool.py` 모두 가능)
- 직접 쓰는 CSS 에는 `url(`, `@import`, `<` 를 쓸 수 없습니다. 배경 사진은 `theme.backgroundImage` 로 넣으세요.

## 설치 없이 쓰기 (편집기)

`editor/index.html` 파일을 브라우저로 열면 됩니다. 터미널이 필요 없습니다.

- 위쪽 **명령 입력** 칸에 명령을 적고 Enter 를 누릅니다. 아래 버튼을 누르면 명령이 채워집니다.
- 명령 예: `set site.name 민수의 작업실`, `design warm-orange`, `add-project 이름 | 2026-11-03 | 요약 | https://...`, `check`
- 오른쪽 미리보기가 바로 바뀝니다. 페이지별 파일은 **받기** 버튼으로 내려받습니다.
- **설정 저장 (파일)** 로 전체 내용을 파일로 보관하고, **설정 불러오기** 로 다시 엽니다.
- **글 쓰기** 칸: 페이지를 고르고 칸에 바로 적으세요. 줄 바꿈이 필요한 글도 됩니다. 사업, 소식 같은 목록은 **항목 더하기** 와 **이 항목 빼기** 로 고칩니다.
- **미리보기** 에서는 모든 페이지를 골라 볼 수 있습니다.

### 이미 올린 홈페이지를 이어서 고치기

1. GitHub 저장소를 **Code → Download ZIP** 으로 받아 압축을 풉니다.
2. 편집기에서 **내 홈페이지 폴더 불러오기** 를 누르고 압축을 푼 **폴더**를 고릅니다.
3. 고친 뒤 **프로젝트 내려받기 (zip)** 으로 받아, 저장소에 다시 올리면 배포가 다시 실행됩니다.

> 주의: GitHub 웹에서 파일을 다시 올리면 지운 파일은 저장소에 그대로 남습니다. 사진을 뺐다면 저장소의 `public/images/` 에서 그 파일도 지우세요.

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
- 사진은 `public/images/` 에 넣고, 설정에서는 `/images/파일이름.jpg` 로 적습니다. 첫 화면은 `home.hero.image`, 다른 페이지는 `페이지이름.image` 와 `페이지이름.imageAlt`(사진 설명)를 씁니다.
- 편집기에서는 페이지를 고르고 **사진 올리기** 로 넣고, **사진 빼기** 로 뺍니다. 빼면 그 사진 파일도 지워집니다.
- 배포하면 `dist/` 의 파일이 공개됩니다. 개인정보는 넣지 마세요.
