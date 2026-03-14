# Frontend View Models

## 1. 목적

- 본 문서는 외부 API/DB 원본 데이터를 프론트 템플릿에서 직접 쓰지 않고, 화면 전용 view-model로 변환하는 기준을 정의한다.
- 목표는 템플릿 단순화, 포맷 일관성, API 교체 유연성을 확보하는 것이다.

## 2. 왜 view-model이 필요한가

- 외부 API 필드명은 길고 일관되지 않다.
- 같은 의미라도 API마다 필드 구조가 다르다.
- 템플릿에서 날짜, 금액, 상태, 배지를 직접 조합하면 복잡도가 커진다.
- Drawer, 리스트, 타임라인, 확장행은 서로 필요한 필드가 다르다.

즉, 원본 -> 정규화 DB -> view-model -> 템플릿 흐름이 적절하다.

## 3. 계층 구조

```text
G2B OpenAPI / Playwright
        ->
정규화 DB 엔터티
        ->
application/service layer
        ->
view-model mapper
        ->
Jinja2 template / HTMX partial
```

## 4. 기본 원칙

- 템플릿은 가능한 한 화면 친화 필드만 사용한다.
- 날짜/금액/상태 문자열은 mapper에서 완성한다.
- `bid_id`는 모든 화면용 모델의 기준 키로 유지한다.
- 원본 필드는 템플릿에서 직접 참조하지 않는다.

## 5. 주요 view-model 정의

### 5.1 `BidListItemVM`

용도:

- 메인 입찰 공고 리스트 행 렌더링

예시 구조:

```python
{
  "bid_id": "R26BK00000001-000",
  "row_number": 1,
  "favorite": True,
  "status": "검토중",
  "status_variant": "primary",
  "business_type": "용역",
  "domain_type": "내자",
  "notice_type": "등록공고",
  "bid_no": "R26BK00000001-000",
  "title": "2026년 중소기업 인력지원사업 종합관리시스템 유지보수 용역",
  "notice_org": "조달청 경남지방조달청",
  "demand_org": "중소벤처기업진흥공단",
  "date_summary": {
    "posted": "2026-03-12 21:13",
    "closed": "2026-03-18 14:00",
    "opened": "2026-03-18 15:00"
  },
  "stage_label": "입찰공고",
  "step_label": "공고등록",
  "progress_label": "진행완료",
  "summary_badge": "검토중"
}
```

### 5.2 `BidDrawerOverviewVM`

용도:

- Drawer `개요` 탭의 2열 상세 테이블 렌더링

예시 구조:

```python
{
  "bid_id": "R26BK00000001-000",
  "title": "2026년 사회적 고립청년 지원사업 운영 용역",
  "status": "검토중",
  "status_variant": "primary",
  "detail_rows": [
    {
      "left_label": "공고종류",
      "left_value": "실공고(등록공고)",
      "right_label": "게시일시",
      "right_value": "2026-03-12 21:13:29"
    }
  ]
}
```

### 5.3 `BidQualificationVM`

용도:

- Drawer `자격/제한` 탭 렌더링

예시 구조:

```python
{
  "industry_limited": True,
  "international_bid": "국내입찰",
  "rebid_allowed": "허용",
  "bid_participation_limit": "없음",
  "consortium_method": "공동수급불허",
  "license_limits": ["소프트웨어사업자(컴퓨터관련서비스사업)"],
  "permitted_industries": ["데이터서비스"],
  "regions": ["전국"],
  "qualification_summary": "소프트웨어사업자 등록 및 유사 유지보수 수행 실적 필요",
  "business_specific": {
    "type": "service",
    "items": [
      {"label": "용역구분", "value": "일반용역"},
      {"label": "기술평가비율", "value": "80"}
    ]
  }
}
```

### 5.4 `BidAttachmentVM`

용도:

- Drawer `첨부파일` 탭 렌더링

예시 구조:

```python
{
  "items": [
    {
      "name": "제안요청서.hwpx",
      "type": "e발주",
      "source": "e발주",
      "url": "#",
      "download_label": "다운로드"
    }
  ]
}
```

### 5.5 `TimelineStageVM`

용도:

- Drawer 타임라인 탭
- 확장행 인라인 타임라인

예시 구조:

```python
{
  "items": [
    {
      "stage": "사전규격",
      "status": "완료",
      "status_variant": "success",
      "number": "R26BD00019757",
      "date": "2026-03-10 09:00",
      "meta": "의견등록마감 2026-03-12"
    }
  ]
}
```

### 5.6 `BidHistoryVM`

용도:

- Drawer `이력` 탭 렌더링

예시 구조:

```python
{
  "items": [
    {
      "changed_at": "2026-03-12 10:12",
      "item": "공고명",
      "before": "중소기업 인력지원사업 유지보수",
      "after": "2026년 중소기업 인력지원사업 종합관리시스템 유지보수 용역"
    }
  ]
}
```

### 5.7 `DashboardSummaryVM`

용도:

- 요약 카드 영역

예시 구조:

```python
{
  "items": [
    {"label": "신규 공고", "value": "12"},
    {"label": "오늘 마감", "value": "3"}
  ],
  "last_synced_at": "2026-03-12 19:45"
}
```

## 6. 업무구분별 보조 모델

### `ServiceBusinessInfoVM`

- 용역구분
- 공공조달분류
- 기술평가비율
- 가격평가비율
- 정보화사업 여부

### `GoodsBusinessInfoVM`

- 물품분류 제한
- 제조 여부
- 세부품명번호
- 세부품명
- 수량
- 인도조건

### `ConstructionBusinessInfoVM`

- 주공종
- 공사현장지역
- 업종평가비율
- 지역의무공동도급
- 건산법 적용 여부
- 상호시장진출 허용 여부

설계 메모:

- 템플릿에서는 이 보조 모델을 그대로 쓰기보다 `business_specific.items[]`로 변환하면 렌더링이 단순해진다.

## 7. mapper 설계 예시

권장 함수 예시:

```python
def build_bid_list_item_vm(bid: Bid) -> dict: ...
def build_bid_drawer_vm(bid_id: str) -> dict: ...
def build_timeline_vm(bid_id: str) -> dict: ...
def build_dashboard_summary_vm() -> dict: ...
```

또는 화면 단위로:

```python
def build_bids_page_vm() -> dict:
    return {
        "summary": ...,
        "bids": [...],
        "selected_bid": ...,
    }
```

## 8. 템플릿과 view-model 연결 규칙

### 페이지 템플릿

- 페이지 템플릿은 화면 단위 view-model을 받는다.
- 예: `bids_page_vm`

### partial 템플릿

- partial은 해당 영역에 필요한 최소 모델만 받는다.
- 예:
  - `_bid_table_rows.html` -> `bids`
  - `_drawer_overview.html` -> `bid_overview`
  - `_drawer_timeline.html` -> `timeline`

## 9. 지금 코드에서 개선할 방향

현재는 샘플 데이터를 템플릿 친화 구조로 바로 넘기고 있다. 프로토타입 단계에서는 괜찮지만, 실제 구현 시에는 아래처럼 분리하는 것이 좋다.

- `sample raw data`
- `sample mapper`
- `template context`

즉, `app/main.py`에서 직접 템플릿용 딕셔너리를 만드는 방식은 초기 검증용으로만 유지하고, 이후에는 `viewmodels/` 또는 `presentation/` 계층으로 분리하는 것이 적절하다.

## 10. 권장 디렉토리 구조

```text
app/
  presentation/
    viewmodels/
      bids.py
      timeline.py
      dashboard.py
    mappers/
      bid_mapper.py
      timeline_mapper.py
```

## 11. 결론

- 프론트는 원본 API 응답이 아니라 view-model을 기준으로 렌더링해야 한다.
- 가장 중요한 것은 `리스트용 모델`, `Drawer용 모델`, `타임라인용 모델`을 분리하는 것이다.
- 이 계층을 먼저 잡아두면 실제 API/DB로 교체할 때 템플릿 수정 범위를 최소화할 수 있다.
