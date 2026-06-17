<p align="center">
  <img src="../assets/writeonside_logo_light.svg" alt="WriteOnSide 로고" width="96" />
</p>

<h1 align="center">WriteOnSide</h1>

<p align="center">
  <strong>随边记 · 가벼운 Windows 사이드 패널 Markdown 노트 앱.</strong><br />
  디스크의 일반 파일. Obsidian 호환. 항상 화면 가장자리에 대기.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows" alt="Windows 10 및 11" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/version-0.1.0-2ea44f" alt="버전 0.1.0" />
</p>

<p align="center">
  <strong>언어:</strong>
  <a href="../README.md">English</a> |
  <a href="README.zh-CN.md">中文</a> |
  <a href="README.pt.md">Português</a> |
  <a href="README.de.md">Deutsch</a> |
  <a href="README.fr.md">Français</a> |
  <a href="README.nl.md">Nederlands</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.it.md">Italiano</a> |
  <a href="README.hi.md">हिन्दी</a> |
  <a href="README.uk.md">Українська</a>
</p>

WriteOnSide(随边记)는 선택한 폴더에 Markdown 노트를 저장합니다. 비공개 데이터베이스나 필수 클라우드 서비스가 없으므로 동일한 Vault를 WriteOnSide, Obsidian, VS Code 또는 다른 편집기에서 열 수 있습니다.

> [!NOTE]
> WriteOnSide `0.1.0`은 활발히 개발 중인 사전 출시 프로젝트입니다. 업그레이드 전에 중요한 노트를 백업하고 릴리스 노트를 확인하세요.

<p align="center">
  <img src="../assets/screenshots/writeonside-screenshot.png" alt="Windows의 WriteOnSide 사이드 패널" width="720" />
</p>

## 설치

### Windows 빌드 다운로드

[GitHub Releases](https://github.com/Thymine2001/WriteOnSide/releases)에서 최신 `WriteOnSide.exe`를 다운로드하세요.

WriteOnSide는 현재 단일 파일의 휴대용 Windows 앱으로 배포됩니다:

1. `WriteOnSide.exe`를 다운로드합니다.
2. 앱을 보관할 폴더에 둡니다.
3. 실행한 뒤 노트 폴더 또는 기존 Obsidian Vault를 선택합니다.
4. `Ctrl+Shift+Enter`로 패널을 표시하거나 숨깁니다.

서명되지 않은 개발 빌드는 Windows SmartScreen 경고를 표시할 수 있습니다. 실행 전에 이 저장소에서 받은 파일인지 확인하세요.

## 주요 기능

### 사이드 패널

- 테두리 없는 전체 높이 패널, 항상 위에 표시
- 화면 왼쪽 또는 오른쪽 가장자리 레이아웃 설정
- 전역 표시/숨기기 단축키, 기본값 `Ctrl+Shift+Enter`
- 패널 너비, 파일 탐색기 너비, 불투명도 조절
- 부드러운 열기, 닫기, 레이아웃 및 크기 조절
- 시스템 트레이 제어 및 Windows 시작 시 실행(선택)
- 단일 인스턴스 및 다중 모니터 작업 영역 배치

### Markdown 편집

- 실시간 구문 강조가 있는 편집 가능한 Markdown 소스
- 링크와 이미지가 있는 읽기 전용 렌더 모드
- 제목, 강조, 인용, 목록, 작업, 표, 코드, 링크, 이미지, 하이라이트, 글자 색용 서식 도구 모음
- 제목, 태그, 날짜, 별칭 등이 있는 YAML front matter
- 찾기 및 바꾸기, 줄 번호, 개요 탐색, 고정 제목
- 언어 레이블과 원클릭 복사가 있는 fenced 코드 블록
- 글꼴, 글자 크기, 테마, 명령 단축키 설정

### 인터페이스 언어

앱에는 **English**, **中文**, **Português**, **Deutsch**, **Français**, **Nederlands**, **한국어**, **Italiano**, **हिन्दी**, **Українська**가 포함됩니다. **설정 → 일반 → 언어**에서 변경하세요.

### Obsidian 호환성

| 기능 | 지원 |
|---|---|
| 위키 링크: `[[Note]]`, `[[Note\|alias]]`, `[[Note#Heading]]` | 예 |
| 블록 참조: `[[Note#^block-id]]` | 예 |
| 노트 및 이미지 임베드: `![[file]]` | 예 |
| 콜아웃: `> [!note]` | 읽기 모드 |
| 각주, `%%주석%%`, 인라인 `#tags` | 예 |
| 작업 목록: `- [ ]` 및 `- [x]` | 예 |
| 노트 이름 변경 및 들어오는 위키 링크 업데이트 | 예 |

`[[`를 입력하면 노트 자동 완성이 열립니다. 편집 모드에서 `Ctrl+클릭`으로 위키 링크를 따릅니다. 백링크 도구는 현재 노트로 연결된 노트를 나열합니다.

### 파일 및 첨부

- 재귀 검색이 있는 지연 로드 파일 탐색기
- 다중 선택 YAML 태그 필터
- 파일 만들기, 이름 바꾸기, 삭제, 끌기, 미리 보기
- Markdown 및 일반 텍스트/소스 코드 형식 편집
- 노트에 이미지 붙여넣기 또는 끌어다 놓기
- 이식 가능한 상대 링크가 있는 첨부 폴더 설정
- Vault 외부의 원자적 저장 및 타임스탬프 백업
- 확대/축소 및 이동이 있는 이미지 뷰어

## 시스템 요구 사항

**최종 사용자:**

- Windows 10 또는 Windows 11
- 표준 데스크톱 세션; Windows on ARM은 아직 공식 테스트되지 않음

**소스 개발:**

- Python 3.12
- [`requirements.txt`](../requirements.txt)에 나열된 패키지

## 소스에서 실행

```powershell
git clone https://github.com/Thymine2001/WriteOnSide.git
cd WriteOnSide

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\writeonside.py
```

첫 실행 시 노트 폴더 또는 기존 Obsidian Vault를 선택하세요.

## 기본 사용법

- 햄버거 버튼으로 파일 탐색기를 열거나 닫습니다.
- 도구 모음에서 편집/읽기 모드를 전환합니다.
- 도구 모음 또는 파일 탐색기에서 노트를 만듭니다.
- Markdown 노트에 이미지를 직접 붙여넣으면 설정된 첨부 폴더에 복사됩니다.
- 탐색기 하단에서 YAML 태그를 선택해 노트를 필터합니다.
- 설정에서 노트 폴더, 레이아웃, 너비, 불투명도, 테마, 글꼴, 전역 단축키, 도구 모음 단축키를 구성합니다.
- 패널을 닫으면 앱이 숨겨집니다. 전역 단축키나 트레이 메뉴로 다시 표시하세요.

## 테스트

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

현재 소스에는 구성, Markdown 렌더링, 단축키, 저장소, 노트 인덱싱, Obsidian 구문, 위키 링크 이름 변경, 국제화를 다루는 단위 테스트가 있습니다.

## Windows EXE 빌드

릴리스 스크립트는 런타임 의존성 외에 PyInstaller와 PyMuPDF가 필요합니다:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller pymupdf
.\build_release.ps1
```

스크립트는:

1. `VERSION`의 패치 버전을 증가시킵니다.
2. SVG 로고에서 PNG 및 ICO 파일을 생성합니다.
3. PyInstaller로 단일 파일 Windows 실행 파일을 빌드합니다.
4. `dist-native-tree-vX.Y.Z\WriteOnSide.exe`에 씁니다.
5. 최신 릴리스 디렉터리 세 개를 유지합니다.

추가 명령과 문제 해결은 [`BUILDING.md`](../BUILDING.md)를 참고하세요.

## 데이터 위치

| 데이터 | 위치 |
|---|---|
| 노트 및 첨부 | 사용자가 선택한 폴더 또는 Obsidian Vault |
| 설정 | `%LOCALAPPDATA%\WriteOnSide\config.json` |
| 관리형 백업 | `%LOCALAPPDATA%\WriteOnSide\Backups\` |

WriteOnSide는 계정이나 내장 클라우드 서비스가 필요하지 않습니다. 사용자가 Vault를 별도로 구성한 동기화 서비스에 둘 때만 노트가 컴퓨터를 떠납니다.

## 프로젝트 구조

```text
writeonside.py          애플리케이션 진입점
writeonside_app/        애플리케이션 소스 코드
assets/                 SVG, PNG, ICO 리소스
scripts/                빌드 보조 스크립트
tests/                  단위 테스트
licenses/               서드파티 라이선스 텍스트
WriteOnSide.spec        PyInstaller 구성
build_release.ps1       버전 관리 Windows 릴리스 스크립트
BUILDING.md             상세 빌드 안내
THIRD_PARTY_NOTICES.md  의존성 표기 및 라이선스 색인
LICENSE                 WriteOnSide 소스 MIT 라이선스
```

## 라이선스

WriteOnSide 원본 소스 코드는
[MIT 라이선스](../LICENSE) 하에 있습니다.

서드파티 구성 요소는
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)에 나열된 각 라이선스를 따릅니다.

<p align="center">
  <sub>Python | Tkinter | Markdown | Obsidian 호환 일반 파일</sub>
</p>
