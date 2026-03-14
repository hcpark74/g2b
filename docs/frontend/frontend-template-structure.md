# Frontend Template Structure

## 1. 목적

- 본 문서는 Bootstrap 5 + Jinja2 + HTMX 기준의 템플릿 구조 초안을 정의한다.
- 실제 구현 전에 화면 분리 단위, partial 범위, 재사용 컴포넌트 경계를 고정하는 데 목적이 있다.

## 2. 설계 원칙

- 전체 레이아웃과 화면별 본문을 분리한다.
- HTMX로 자주 갱신되는 영역은 partial 템플릿으로 분리한다.
- 메인 리스트와 우측 Drawer는 서로 독립적으로 갱신 가능해야 한다.
- 공통 배지, 카드, 테이블 도구막대는 include 단위로 재사용한다.

## 3. 권장 디렉토리 구조

```text
templates/
  base.html
  layouts/
    app_shell.html
  pages/
    bids/
      index.html
    prespecs/
      index.html
    results/
      index.html
    favorites/
      index.html
    operations/
      index.html
  partials/
    shared/
      _header.html
      _sidebar.html
      _summary_cards.html
      _status_badge.html
      _empty_state.html
      _pagination.html
    bids/
      _filter_bar.html
      _table_toolbar.html
      _bid_table.html
      _bid_table_rows.html
      _drawer.html
      _drawer_overview.html
      _drawer_qualification.html
      _drawer_attachments.html
      _drawer_timeline.html
      _drawer_history.html
    dashboard/
      _sync_banner.html
      _summary_stats.html
```

## 4. 최상위 템플릿 구조

### `templates/base.html`

역할:

- HTML 문서의 최상위 베이스
- `head`, CSS/JS import, 공통 meta, body block 정의

예상 block:

- `title`
- `head_extra`
- `body`
- `scripts`

### `templates/layouts/app_shell.html`

역할:

- 로그인 이후 공통 앱 셸
- 상단 헤더, 좌측 네비게이션, 본문 컨테이너, Drawer 슬롯 정의

예상 block:

- `page_header`
- `page_actions`
- `content`
- `drawer`

## 5. 메인 입찰 공고 화면 템플릿

### `templates/pages/bids/index.html`

역할:

- 메인 입찰 공고 페이지 조합 템플릿
- 공통 셸 위에 요약 카드, 필터, 테이블, Drawer를 배치

예상 구조:

```jinja2
{% extends "layouts/app_shell.html" %}

{% block title %}입찰 공고{% endblock %}

{% block content %}
  {% include "partials/dashboard/_sync_banner.html" %}
  {% include "partials/shared/_summary_cards.html" %}
  {% include "partials/bids/_filter_bar.html" %}
  {% include "partials/bids/_table_toolbar.html" %}

  <section id="bid-table-container">
    {% include "partials/bids/_bid_table.html" %}
  </section>
{% endblock %}

{% block drawer %}
  <section id="bid-drawer-container">
    {% include "partials/bids/_drawer.html" %}
  </section>
{% endblock %}
```

설계 메모:

- `bid-table-container`와 `bid-drawer-container`는 HTMX 부분 갱신 타겟으로 사용한다.

## 6. 메인 화면 partial 설계

### `partials/shared/_header.html`

역할:

- 상단 네비게이션 바
- 서비스명, 빠른 검색, 마지막 동기화 시각, 사용자 메뉴

Bootstrap 권장:

- `navbar`
- `container-fluid`
- `input-group`

### `partials/shared/_sidebar.html`

역할:

- 좌측 메뉴
- 현재 화면 active 상태 표시

Bootstrap 권장:

- `nav flex-column`
- `list-group` 또는 `accordion`

### `partials/shared/_summary_cards.html`

역할:

- 신규 공고, 오늘 마감, 관심 공고, 상태 변경 감지 카드

입력 데이터 예시:

- `new_count`
- `closing_today_count`
- `favorite_count`
- `changed_count`

### `partials/bids/_filter_bar.html`

역할:

- 메인 리스트 필터 영역

포함 요소:

- 키워드 검색
- 공고기관
- 수요기관
- 상태
- 업무구분
- 마감일 범위
- 상세 필터 펼침 버튼

HTMX 적용 방향:

- 필터 submit 시 `#bid-table-container`만 갱신

### `partials/bids/_table_toolbar.html`

역할:

- 총 건수, 정렬, Excel 내보내기, 보기 옵션 제공

포함 요소:

- `전체 n건`
- 정렬 드롭다운
- `Excel 내보내기`
- 필요 시 밀도/컬럼 보기 옵션

### `partials/bids/_bid_table.html`

역할:

- 테이블 헤더, 본문, 페이지네이션을 감싼 컨테이너

내부 구성:

- `_bid_table_rows.html`
- `_pagination.html`

### `partials/bids/_bid_table_rows.html`

역할:

- 실제 테이블 행 반복 렌더링

필수 컬럼:

- 관심 여부
- 상태
- 업무구분
- 공고번호
- 공고명
- 기관
- 추정가격
- 마감일시
- 개찰일시
- 변경 여부

HTMX 적용 방향:

- 행 클릭 시 `#bid-drawer-container` 갱신

예상 속성 예시:

```html
<tr hx-get="/partials/bids/{{ bid.bid_id }}/drawer" hx-target="#bid-drawer-container" hx-swap="innerHTML">
```

## 7. Drawer 템플릿 설계

### `partials/bids/_drawer.html`

역할:

- 우측 Offcanvas/Drawer 전체 구조
- 선택된 공고가 없으면 placeholder 상태 표시

구성:

- Drawer 헤더
- 탭 네비게이션
- 탭 콘텐츠 슬롯

### `partials/bids/_drawer_overview.html`

내용:

- 공고번호/차수
- 공고기관/수요기관
- 공고일/마감일/개찰일
- 예산/추정가격/VAT
- 외부 링크

### `partials/bids/_drawer_qualification.html`

내용:

- 업종 제한 여부
- 면허 제한 목록
- 참가가능지역
- 공동수급 방식
- 참가자격 문구 요약

### `partials/bids/_drawer_attachments.html`

내용:

- 일반 첨부
- e발주 첨부
- 파일명, 유형, 다운로드 링크

### `partials/bids/_drawer_timeline.html`

내용:

- 타임라인 단계
- 낙찰/계약 요약
- 단계별 발생 시각

### `partials/bids/_drawer_history.html`

내용:

- 변경이력 테이블
- 변경 항목, 변경 전값, 변경 후값

## 8. 빈 상태/로딩 상태 템플릿

### `partials/shared/_empty_state.html`

사용 예:

- 검색 결과 없음
- 선택된 공고 없음
- 첨부파일 없음

### 로딩 표시 전략

- HTMX 요청 중에는 버튼 비활성화 + 작은 spinner 표시
- Drawer 로딩은 skeleton보다 단순 spinner + 문구가 실무형 화면에 더 적합할 수 있다.

## 9. 화면별 확장 구조

### `pages/prespecs/index.html`

- 사전 탐색 리스트 본문
- 발주계획/사전규격/조달요청 세그먼트

### `pages/results/index.html`

- 사후 분석 요약 카드
- 낙찰/계약 결과 테이블

### `pages/favorites/index.html`

- 관심 공고 전용 필터
- 메모 중심 리스트

### `pages/operations/index.html`

- 동기화 상태
- 실패 로그
- 작업 이력

## 10. 템플릿 구현 우선순위

### 1차

- `base.html`
- `layouts/app_shell.html`
- `pages/bids/index.html`
- `partials/shared/_header.html`
- `partials/shared/_sidebar.html`
- `partials/shared/_summary_cards.html`
- `partials/bids/_filter_bar.html`
- `partials/bids/_table_toolbar.html`
- `partials/bids/_bid_table.html`
- `partials/bids/_bid_table_rows.html`
- `partials/bids/_drawer.html`
- `partials/bids/_drawer_overview.html`

### 2차

- `partials/bids/_drawer_qualification.html`
- `partials/bids/_drawer_attachments.html`
- `partials/bids/_drawer_timeline.html`
- `partials/bids/_drawer_history.html`
- `partials/shared/_empty_state.html`

### 3차

- `pages/prespecs/index.html`
- `pages/results/index.html`
- `pages/favorites/index.html`
- `pages/operations/index.html`

## 11. 결론

- 템플릿 구조는 `페이지 조합 템플릿 + HTMX partial` 구조가 가장 적절하다.
- 핵심은 메인 리스트와 우측 Drawer를 독립 갱신 가능한 구조로 분리하는 것이다.
- Bootstrap 기준으로는 공통 셸과 partial 분리만 잘해도 구현 난이도를 크게 낮출 수 있다.
