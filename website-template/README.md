# 홈페이지 템플릿 (비영리 단체 기본)

NGO, 사회복지법인, 비영리 법인의 기관 소개와 후원 모금 홈페이지를 기본으로 합니다. 기관 이름, 금액, 계좌, 영수증 발급 방법처럼 사실이 필요한 내용은 직접 확인해서 적어 주세요. 템플릿은 빈칸 안내문만 담고 있습니다.

설정 파일과 콘텐츠 파일을 고치면 홈페이지 파일이 만들어집니다. Node.js 도 AI 도 필요 없고, Python 3 만 있으면 됩니다.

## 처음 시작하기 (5분)

둘 중 하나를 고르면 됩니다.

**A. 브라우저에서 (터미널 없이)**

> 편집기 열기: 저장소를 **Code → Download ZIP** 으로 받아 압축을 풀고, `website-template/editor/index.html` 을 Chrome 이나 Edge 로 여세요. GitHub 화면에서 파일을 열면 코드만 보이므로 zip 으로 받아야 합니다. (더블클릭해도 메모장으로 열리면 **연결 프로그램 → 브라우저** 를 고르세요.)

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
| 버튼 모양 | square, soft, round, pill | `theme.buttonShape` |
| 현재 메뉴 표시 | underline, background, border, side | `theme.menuMark` |
| 메뉴를 화면 위에 고정 | true, false (기본 false) | `theme.menuSticky` |
| 버튼 크기 | normal, large (기본 normal) | `theme.buttonSize` |
| 알림 띠 | 기본은 꺼짐. 켜면 홈 맨 위에 한 줄 | `content/banner.json` (active, text, link) |
| 브랜드 색 추천 | 대표색 하나로 버튼·링크·배경·글자 색을 규칙으로 계산 | `python scripts/palette.py #RRGGBB` |
| 예시 기관 | 가상의 지역복지관, 가상의 청소년 센터, 빈 설정 | `python scripts/build_example.py community-welfare` |
| 글꼴 역할 | base, heading, body, menu, button, quote 마다 글꼴 선택 (적지 않으면 base 를 따름) | `config/design.json` 의 `fonts` |
| 글꼴 파일 | 굵기마다 WOFF2 파일, 쓰는 파일만 사이트에 복사, 외부 서비스 사용 안 함 | `fonts/registry.json`, `fonts/files` |
| 글꼴과 함께 zip | 홈페이지 파일, 글꼴, 라이선스를 한 zip 으로 | `python scripts/package.py --out site.zip` |

글꼴 파일은 개발할 때 `python scripts/fetch_fonts.py` 로 한 번 받아 둡니다. 편집실의 zip 내려받기에는 글꼴 파일이 들어가지 않으므로, 글꼴까지 담은 배포 묶음은 `scripts/package.py` 로 만드세요.

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

### 관리자 게시판 (공지, 자료 올리기)

- 게시판 페이지(`/board`)는 글 목록입니다. 편집기의 **글 쓰기** 칸에서 페이지를 **게시판** 으로 고르고, **항목 더하기** 로 글을 씁니다.
- 글마다 **본문** 칸이 있고, 본문은 방문자가 **자세히 보기** 를 눌러야 펼쳐집니다. 줄 바꿈도 그대로 보입니다.
- 글을 쓰고 zip 으로 받아 저장소에 올리면 게시판이 바뀝니다. 편집기가 관리자 화면 역할을 합니다.

**한계 (계정 없이 할 수 없는 것)**
- 방문자가 직접 글을 쓰거나 댓글을 다는 기능은 서버가 필요합니다. GitHub Pages 는 정적 페이지만 보여 주므로 이 프로그램만으로는 만들 수 없습니다. 방문자 글은 외부 신청 양식 서비스를 연결하는 방법이 있습니다.
- 관리자 로그인도 서버가 필요합니다. 편집기는 관리자 본인의 컴퓨터 브라우저에서만 열고, 저장소 쓰기 권한은 GitHub 계정으로 관리합니다.

### 계정 없이 할 수 있는 범위

계정 없이는 완성된 홈페이지 파일(zip)까지 만들 수 있습니다. 공개 주소, 자동 배포, 방문자 글쓰기는 계정이나 서버가 필요합니다. 자세한 범위와 수치는 [계정 없이 범위](docs/계정-없이-범위.md) 를 보세요.

### Cloudflare · Supabase 연결

Cloudflare 로 배포하거나 Supabase 로 게시판 글 저장과 관리자 로그인을 붙이려면 [연결 가이드](docs/연결-가이드.md) 를 보세요. 두 서비스는 각각 가입이 필요합니다.

Supabase 에 가입했다면 편집기의 **Supabase 연결** 칸에 프로젝트 주소와 anon 키를 넣으세요. 연결하면 게시판에 방문자 글 칸이 생기고, 공개 주소 뒤에 `/admin.html` 을 붙인 관리자 화면에서 글을 승인하거나 지울 수 있습니다. 비밀 키(service_role)는 넣으면 검사가 막습니다.

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

## 문서에서 소식 초안 만들기 (선택, Node.js 필요)

HWPX, HWP, PDF, DOCX 문서를 읽어 소식 초안을 JSON 으로 만듭니다. 홈페이지 파일(`content/`)은 바꾸지 않습니다. 변환은 인터넷 없이 이루어지고 AI 를 쓰지 않습니다.

```bash
cd tools/import-draft
npm install          # 처음 한 번 (kordoc 4.23.1 을 설치합니다)
npm test             # 확인 (테스트 9건)
node import.mjs ~/받은파일/소식.hwpx ~/받은파일/안내.pdf
```

- 결과는 `drafts/<파일이름>.draft.json` 에 생깁니다. `drafts/` 는 저장소에 올라가지 않습니다.
- `suggestedNewsItem` 의 `title`, `date`, `summary` 를 확인하고 `content/news.json` 의 `items` 에 붙여 넣습니다. `body`, `bullets`, `tables` 는 참고용입니다.
- `warnings` 에 나온 내용은 반드시 확인하세요. 날짜가 없거나, 전화번호나 주민등록번호 모양의 숫자가 있으면 알려 줍니다. 주민등록번호 모양은 초안에서 가려 집니다.
- 암호가 걸린 문서는 읽지 않고 건너뜁니다.
- 스캔한 그림 문서(글자가 없는 PDF)는 글을 찾지 못합니다. 이 도구는 OCR 을 쓰지 않습니다.

## GitHub 에 보내기 (선택)

터미널에서 고친 홈페이지를 승인된 GitHub 저장소와 브랜치로 보냅니다. 편집기에서는 쓰지 않습니다.

1. `config/sync.json` 에 보낼 곳을 적습니다. 예: `{"repo": "sunnykim717/claude-project", "branch": "claude/내-작업-브랜치"}`
2. `python scripts/site_tool.py sync` 로 보낼 파일을 확인합니다. 아무것도 바뀌지 않습니다.
3. 괜찮으면 `python scripts/site_tool.py sync --push` 로 커밋하고 올립니다.

보내기를 막는 경우는 다음과 같습니다.
- origin 이 적은 저장소가 아닐 때
- 현재 브랜치가 적은 브랜치가 아닐 때
- `main`, `master` 같은 기본 브랜치일 때 (공개 배포로 이어지므로 보내지 않습니다)
- 원격 브랜치에 내 기록에 없는 새 커밋이 있을 때 (먼저 받아서 합치세요. 강제로 보내지 않습니다)

커밋에는 이 홈페이지 폴더의 변경만 담깁니다. 인증 정보는 git 이 이미 가진 로그인을 그대로 씁니다. 이 도구는 토큰을 저장하지 않습니다.

## 주의

- 링크는 `https://` 주소 또는 이 템플릿의 페이지 주소(`/about` 등)만 쓸 수 있습니다.
- 날짜는 `2026-01-15` 형식으로 적습니다.
- 사진은 `public/images/` 에 넣고, 설정에서는 `/images/파일이름.jpg` 로 적습니다. 첫 화면은 `home.hero.image`, 다른 페이지는 `페이지이름.image` 와 `페이지이름.imageAlt`(사진 설명)를 씁니다.
- 편집기에서는 페이지를 고르고 **사진 올리기** 로 넣고, **사진 빼기** 로 뺍니다. 빼면 그 사진 파일도 지워집니다.
- 배포하면 `dist/` 의 파일이 공개됩니다. 개인정보는 넣지 마세요.
