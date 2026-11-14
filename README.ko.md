# Princess Maker: Children of Revelation — TableData & Bundle 도구

[English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | **한국어**

**Princess Maker: Children of Revelation**(Steam)용 Windows GUI 도구입니다. 게임의 AssetBundle을 복호화하고, 암호화된 `TableData`를 추출·편집할 수 있으며, 패치 파일로 게임 업데이트 후에도 수정 내용을 유지할 수 있습니다.

UI 언어: 繁體中文 / 简体中文 / English / 日本語 / 한국어 (오른쪽 위에서 전환).

## 기능

- **Bundle 복호화** — `packedassets_assets_all_*.bundle`을 그 자리에서 복호화합니다(먼저 `.bak` 백업을 만듭니다).
- **TableData 추출 / 편집** — `resources.assets`에서 `TableData`를 꺼내 복호화하고, SQLite 데이터베이스와 테이블별 JSON을 만듭니다.
- **데이터베이스 보기** — 테이블 검색, 행 Filter, 셀 더블클릭 편집, 읽기 전용 SQL 입력란. 수정 후에도 원래 자료형(숫자, 불리언, 배열)이 유지됩니다.
- **다시 암호화하여 출력** — `TableData_modified.txt`를 만들고, [UABEANext](https://github.com/nesrak1/UABEANext)로 `resources.assets`에 가져옵니다(Import). 이 도구 자체는 `resources.assets`를 덮어쓰지 않습니다.
- **패치 파일** — 수정 내용을 작은 패치로 저장해 두었다가 게임 업데이트 후 다시 적용할 수 있습니다.

## 설치 및 실행

### 방법 A: exe 다운로드 (가장 간단)

[Releases](../../releases) 페이지에서 `PrincessMakerTool.exe`를 받으세요. 전용 폴더에 두는 것을 권장합니다. 도구가 exe 옆에 작업 파일을 만듭니다. Python은 필요하지 않습니다.

### 방법 B: 소스로 실행

Python 3.10 이상이 필요합니다:

```bash
pip install -r requirements.txt
python PrincessMakerTool.py
```

## 기본 사용 순서

1. 게임 폴더(`PrincessMakerKaren_Data`가 들어 있는 폴더)를 선택하고 **자동 찾기**를 누릅니다.
2. **Bundle 복호화** 탭 → Bundle 복호화(한 번만 하면 됩니다).
3. **TableData** 탭:
   1. resources.assets에서 추출 후 복호화
   2. 데이터베이스 생성 + JSON 내보내기
4. **데이터베이스 보기 / 편집** 탭 → 테이블 이름을 클릭하고 셀을 더블클릭해 수정한 뒤 '수정 저장'을 누릅니다.
5. **TableData** 탭 → 3단계 '다시 암호화하여 TableData_modified.txt 출력'.
6. UABEANext로 `resources.assets`를 열어 `TableData_modified.txt`를 `TableData`에 가져온 뒤 저장합니다.

`tables/`의 JSON을 직접 수정한 다음 'tables에서 다시 불러오기'를 눌러도 됩니다.

## 게임 업데이트 후에도 수정 내용 유지하기

게임이 업데이트되면 `TableData`가 교체되므로 이전 데이터에서 한 수정은 사라집니다. 패치를 사용하세요:

1. **패치 만들기 (내 수정 저장)** — 원본 데이터와의 차이만 기록하며, 각 행의 고유 ID 열로 위치를 찾습니다.
2. 게임을 업데이트한 뒤 1, 2단계(추출 + 데이터베이스 생성)를 다시 실행합니다.
3. **패치 적용 (내 수정 복원)** — 새 데이터에 패치를 적용합니다.
4. 3단계로 출력 → 다시 UABEANext로 가져옵니다.

게임 쪽에서도 내가 수정한 셀을 바꿨다면, 내 값으로 덮어쓸지 게임의 새 값을 유지할지 묻습니다. 대응하지 못한 항목(행 삭제, 열 이름 변경, 테이블 사라짐)은 조용히 버려지지 않고 `patches/apply_report_*.txt`에 나열됩니다.

안전장치: 2단계는 `tables/`를 덮어쓰기 전에 현재 수정 내용을 `patches/auto_before_reexport_*.json`으로 자동 저장합니다.

## exe 옆에 만들어지는 파일

| 경로 | 용도 |
|---|---|
| `TableData.dec.bin` | 복호화된 TableData |
| `TableData.db` | 보기 화면에서 쓰는 SQLite 데이터베이스 |
| `tables/` | 테이블별 JSON(편집용 사본) |
| `tables_orig/` | 수정하지 않은 원본 사본(패치 비교 기준) |
| `patches/` | 패치 파일과 적용 보고서 |
| `TableData_modified.txt` | 최종 출력(UABEANext로 가져오기) |
| `pm_tool_settings.json` | 언어와 마지막 게임 폴더 |

## exe 직접 빌드하기

`PrincessMakerTool.py`, `requirements.txt`, `build.bat`을 한 폴더에 두고 `build.bat`을 더블클릭하세요. 결과물은 `dist\PrincessMakerTool.exe`입니다.

## 참고 사항

- Windows 전용입니다(빌드 스크립트와 경로는 Windows용 Steam 버전 기준).
- 게임 파일은 반드시 백업하세요. Steam → '게임 파일 무결성 검사'로 복원할 수 있습니다.
- 서명되지 않은 단일 파일 exe는 백신이나 SmartScreen에서 오탐될 수 있습니다. 걱정되면 소스에서 직접 빌드하세요.
- 고유 ID 열이 없는 테이블은 패치에서 행 위치로 대응시키므로, 업데이트 후 신뢰도가 떨어집니다.

## 면책 조항

이 도구는 비공식 팬 제작 도구이며 게임 개발사 및 퍼블리셔와 관련이 없습니다. 게임 데이터는 포함되어 있지 않습니다. 합법적으로 구입한 게임 사본에만, 본인 책임하에 사용하세요.

**AI 생성 코드:** 이 저장소의 코드는 AI(Anthropic의 Claude)가 생성했습니다. 우려되는 점이 있다면 소스 코드를 직접 확인하시고, 게임 파일은 반드시 백업해 두세요.
