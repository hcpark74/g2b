# Frontend UI Tokens

## 1. 목적

- 본 문서는 Bootstrap 5 기반 UI의 색상, 상태 배지, 버튼, 테이블 스타일 토큰을 정의한다.
- 목표는 나라장터 친화형 톤을 유지하면서도, 내부 화면 전체에서 일관된 시각 언어를 확보하는 것이다.

## 2. 디자인 방향

- 기본 톤은 `blue-grey + off-white`
- 강조는 제한적으로 사용
- 상태 표현은 명확하게, 장식은 최소화
- Bootstrap 기본 색을 그대로 쓰기보다 운영 화면에 맞게 desaturated tone으로 조정

## 3. 컬러 토큰

### 기본 배경

| 토큰 | 용도 | 권장 값 |
|---|---|---|
| `--bg-app` | 앱 전체 배경 | `#f4f6f8` |
| `--bg-surface` | 카드/패널 배경 | `#ffffff` |
| `--bg-subtle` | 필터 패널, 안내 박스 배경 | `#eef2f6` |
| `--bg-table-head` | 테이블 헤더 배경 | `#edf1f5` |

### 텍스트

| 토큰 | 용도 | 권장 값 |
|---|---|---|
| `--text-primary` | 기본 본문 | `#1f2933` |
| `--text-secondary` | 보조 설명 | `#52606d` |
| `--text-muted` | 약한 텍스트 | `#7b8794` |
| `--text-link` | 링크 | `#1d4ed8` |

### 경계선

| 토큰 | 용도 | 권장 값 |
|---|---|---|
| `--border-default` | 일반 보더 | `#d9e2ec` |
| `--border-strong` | 구분 강조 | `#bcccdc` |
| `--border-focus` | 포커스 | `#5b8def` |

### 브랜드/포인트

| 토큰 | 용도 | 권장 값 |
|---|---|---|
| `--brand-primary` | 주요 액션, 활성 탭 | `#3d6fd6` |
| `--brand-primary-hover` | 주요 액션 hover | `#325fc0` |
| `--brand-soft` | 강조 배경 | `#e7eefc` |

## 4. 상태 배지 토큰

### 운영 상태

| 상태 | 토큰 이름 | 배경 | 텍스트 | 의미 |
|---|---|---|---|---|
| 수집완료 | `--status-collected` | `#e9eef5` | `#486581` | 기본 완료 |
| 검토중 | `--status-reviewing` | `#e8f1ff` | `#1d4ed8` | 실무 검토 중 |
| 관심 | `--status-favorite` | `#fff3d6` | `#b26a00` | 우선 확인 대상 |
| 투찰완료 | `--status-submitted` | `#e6f7ed` | `#18794e` | 제출 완료 |
| 낙찰 | `--status-won` | `#dcfce7` | `#166534` | 결과 확정 |
| 보관 | `--status-archived` | `#f1f5f9` | `#64748b` | 후순위/보관 |

### 단계 상태

| 상태 | 토큰 이름 | 배경 | 텍스트 | 의미 |
|---|---|---|---|---|
| 완료 | `--stage-complete` | `#e8f7ee` | `#18794e` | 단계 완료 |
| 진행중 | `--stage-active` | `#e8f1ff` | `#1d4ed8` | 현재 진행 |
| 미도달 | `--stage-pending` | `#f1f5f9` | `#6b7280` | 아직 없음 |
| 미체결 | `--stage-unresolved` | `#fff4e5` | `#b45309` | 계약 미확정 |
| 확인 필요 | `--stage-warning` | `#fff1f2` | `#be123c` | 예외/확인 필요 |

### 기타 업무 신호

| 상태 | 토큰 이름 | 배경 | 텍스트 | 의미 |
|---|---|---|---|---|
| 마감임박 | `--signal-deadline` | `#fee2e2` | `#b91c1c` | 우선 조치 |
| 변경감지 | `--signal-changed` | `#fff0e1` | `#c2410c` | 변경 발생 |
| 첨부존재 | `--signal-attachment` | `#eef2ff` | `#4338ca` | 첨부 있음 |

## 5. 버튼 토큰

### 버튼 역할

| 버튼 유형 | Bootstrap 기준 | 용도 |
|---|---|---|
| Primary | `btn btn-primary` | 검색, 저장, 재수집 |
| Secondary | `btn btn-secondary` | 일반 보조 액션 |
| Outline | `btn btn-outline-secondary` | 필터 확장, 초기화 |
| Success | `btn btn-success` | 확정/완료 계열 |
| Warning | `btn btn-warning` | 주의 필요 액션 |
| Danger | `btn btn-danger` | 파괴적 액션 |

### 프로젝트 적용 규칙

- `검색`, `수동 동기화`, `다시 읽어오기`는 `primary`
- `초기화`, `상세조건`, `더보기`는 `outline`
- `엑셀 다운로드`는 `success` 또는 커스텀 녹색 outline
- `즐겨찾기`는 아이콘 버튼 + active 시 amber 강조

## 6. 테이블 토큰

### 기본 규칙

- 헤더는 연한 회색 배경
- 셀 패딩은 Bootstrap 기본보다 약간 축소
- 행 hover는 약하게
- 선택 행은 약한 파란 배경

### 권장 값

| 토큰 | 용도 | 권장 값 |
|---|---|---|
| `--table-row-hover` | hover 배경 | `#f8fbff` |
| `--table-row-selected` | 선택 배경 | `#eef4ff` |
| `--table-border` | 행 경계 | `#e5e7eb` |
| `--table-title-link` | 공고명 링크 | `#2563eb` |

## 7. 카드 토큰

### 요약 카드

- 배경: `#ffffff`
- 제목: 보조 텍스트
- 숫자: 진한 텍스트
- 우측 상단 작은 배지 허용

### 단계 카드

- 기본 배경: `#ffffff`
- 완료 단계: 좌측 상단 또는 상단 보더로 상태 표현
- 카드 내부는 최대 4줄로 제한

## 8. 폼 토큰

### 입력 필드

- 배경: 흰색
- 기본 보더: `--border-default`
- focus: `--border-focus`
- 높이: Bootstrap 기본 또는 약간 축소

### 필터 패널

- 배경: `--bg-subtle`
- 보더: `--border-default`
- 그룹 간 간격은 촘촘하게 유지

## 9. CSS 변수 예시

```css
:root {
  --bg-app: #f4f6f8;
  --bg-surface: #ffffff;
  --bg-subtle: #eef2f6;
  --bg-table-head: #edf1f5;

  --text-primary: #1f2933;
  --text-secondary: #52606d;
  --text-muted: #7b8794;
  --text-link: #1d4ed8;

  --border-default: #d9e2ec;
  --border-strong: #bcccdc;
  --border-focus: #5b8def;

  --brand-primary: #3d6fd6;
  --brand-primary-hover: #325fc0;
  --brand-soft: #e7eefc;
}
```

## 10. 구현 메모

- Bootstrap 변수 전체를 커스터마이징하기보다, 프로젝트 전용 CSS 변수와 보조 유틸 클래스를 먼저 두는 것이 효율적이다.
- 상태 배지는 Bootstrap 기본 `badge` 위에 프로젝트 전용 클래스를 입혀 관리한다.
- 테이블은 Bootstrap 기본 `table`을 사용하되, 헤더/hover/선택 상태만 프로젝트 스타일로 덮어쓴다.

## 11. 결론

- 이 프로젝트의 UI는 밝고 차분한 관리형 화면이 적합하다.
- 핵심은 `파란 구조`, `회색 정보 배경`, `절제된 상태 강조`, `높은 정보 밀도`다.
