# Frontend Main HTML Blocks

## 1. 목적

- 본 문서는 메인 `입찰 공고` 화면의 실제 HTML 블록 구조 초안을 정의한다.
- 기준은 `Bootstrap 5 + Jinja2 + HTMX`다.

## 2. 최상위 구조

```html
<body>
  <div id="app-shell">
    <header id="top-header"></header>
    <div id="app-body" class="container-fluid">
      <aside id="left-sidebar"></aside>
      <main id="main-content"></main>
      <section id="bid-drawer-container"></section>
    </div>
  </div>
</body>
```

## 3. 메인 콘텐츠 블록

```html
<main id="main-content" class="flex-grow-1">
  <section id="page-header"></section>
  <section id="sync-banner"></section>
  <section id="summary-cards"></section>
  <section id="filter-panel"></section>
  <section id="table-toolbar"></section>
  <section id="bid-table-container"></section>
</main>
```

## 4. 블록별 역할

### `#top-header`

- 서비스명
- 마지막 동기화 시각
- 빠른 검색
- 사용자 메뉴

### `#left-sidebar`

- 메인 메뉴
- 현재 화면 active 표시

### `#page-header`

- 페이지 제목
- 브레드크럼
- 우측 액션 버튼 (`수동 동기화`)

### `#sync-banner`

- 최근 배치 성공/실패 상태
- 경고 메시지

### `#summary-cards`

- 신규 공고
- 오늘 마감
- 관심 공고
- 상태 변경 감지

### `#filter-panel`

- 기본 검색 조건
- 상세 조건 펼침
- 검색/초기화 버튼

### `#table-toolbar`

- 총 건수
- 정렬
- 페이지 크기
- 엑셀 다운로드

### `#bid-table-container`

- 공고 테이블
- 페이지네이션

### `#bid-drawer-container`

- 우측 상세 Drawer
- HTMX로 독립 갱신

## 5. Jinja2 조합 예시

```jinja2
{% extends "layouts/app_shell.html" %}

{% block content %}
  <section id="page-header">
    {% include "partials/shared/_page_header.html" %}
  </section>

  <section id="sync-banner">
    {% include "partials/dashboard/_sync_banner.html" %}
  </section>

  <section id="summary-cards">
    {% include "partials/shared/_summary_cards.html" %}
  </section>

  <section id="filter-panel">
    {% include "partials/bids/_filter_bar.html" %}
  </section>

  <section id="table-toolbar">
    {% include "partials/bids/_table_toolbar.html" %}
  </section>

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

## 6. HTMX 타겟 규칙

- 필터 변경 -> `#bid-table-container` 갱신
- 정렬/페이지 이동 -> `#bid-table-container` 갱신
- 행 클릭 -> `#bid-drawer-container` 갱신
- 즐겨찾기 토글 성공 -> 현재 행 또는 `#bid-table-container` 부분 갱신

예시:

```html
<form hx-get="/partials/bids/table" hx-target="#bid-table-container" hx-swap="innerHTML">
```

```html
<tr hx-get="/partials/bids/{{ bid.bid_id }}/drawer" hx-target="#bid-drawer-container" hx-swap="innerHTML">
```

## 7. Bootstrap 권장 클래스

- 상단 헤더: `navbar`, `navbar-expand`, `border-bottom`
- 본문 레이아웃: `d-flex`, `flex-grow-1`
- 필터 패널: `card`, `card-body`, `row`, `g-2`
- 테이블: `table`, `table-sm`, `table-hover`, `align-middle`
- Drawer: `offcanvas offcanvas-end`
- 요약 카드: `card`, `shadow-sm`, `h-100`

## 8. 실제 구현 우선순위

1. `#page-header`
2. `#filter-panel`
3. `#table-toolbar`
4. `#bid-table-container`
5. `#bid-drawer-container`
6. `#summary-cards`
7. `#sync-banner`

## 9. 확장행 상세 블록 옵션

통합 검색/사전 탐색 화면에서는 Drawer 대신 행 하단 확장 상세 블록을 사용할 수 있다.

예상 구조:

```html
<tbody>
  <tr class="bid-row"></tr>
  <tr class="bid-expanded-row d-none">
    <td colspan="12">
      <section class="timeline-inline-panel" id="timeline-inline-{{ bid.bid_id }}"></section>
    </td>
  </tr>
</tbody>
```

포함 내용:

- 진행/미진행 상태 배지
- 단계 카드 목록
- 단계별 번호/일자/상태

HTMX 적용 방향:

- `더보기` 클릭 시 해당 확장행 내부만 갱신

예시:

```html
<button hx-get="/partials/bids/{{ bid.bid_id }}/timeline-inline" hx-target="#timeline-inline-{{ bid.bid_id }}" hx-swap="innerHTML">
```

## 10. 결론

- 메인 화면은 `필터 패널 + 테이블 + 우측 Drawer` 세 축으로 구현하면 된다.
- HTMX는 `bid-table-container`, `bid-drawer-container` 두 개를 핵심 갱신 지점으로 잡는 것이 가장 단순하다.
- 통합 검색/사전 탐색 화면은 `행 확장형 타임라인`을 보조 패턴으로 도입할 수 있다.
