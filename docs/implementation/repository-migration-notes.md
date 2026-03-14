# Sample vs SQLModel Field Notes

샘플 데이터 경로와 `SqlModelBidRepository` 경로 사이의 필드 차이와 매핑 메모를 정리한다.

## 1. 공통 목표

- `app.presentation.mappers.bid_mapper.py`가 두 데이터 소스를 같은 계약으로 다룰 수 있게 유지한다.
- 템플릿은 가능한 한 raw source 차이를 직접 알지 않도록 한다.
- SQLModel 경로에서 아직 없는 값은 fallback 또는 placeholder로 명시한다.

## 2. 리스트 공통 필드

두 경로 모두 아래 필드는 동일 이름으로 mapper에 전달한다.

- `bid_id`
- `bid_no`
- `title`
- `notice_org`
- `demand_org`
- `status`
- `status_variant`
- `business_type`
- `budget_amount`
- `posted_at`
- `closed_at`
- `opened_at`
- `stage_label`
- `step_label`
- `progress_label`
- `favorite`

## 3. 주요 차이

### A. 상태값

- 샘플 데이터: `status`와 `status_variant`가 이미 화면 친화형 문자열로 들어 있다.
  - 예: `status="검토중"`, `status_variant="primary"`
- SQLModel 데이터: DB에는 상태 코드가 저장되고 repository에서 라벨/variant로 변환한다.
  - 예: `reviewing -> 검토중`, `primary`

정리:

- 화면 계약은 유지하되 상태 코드 해석 책임은 repository에 둔다.

### B. 공고번호 표현

- 샘플 데이터: `bid_no`에 `R26BK...-000`처럼 차수까지 포함된 표시값이 들어 있다.
- SQLModel 데이터: `bid_no`는 원 공고번호만 유지하고, `bid_id`가 `{bid_no}-{bid_seq}` 역할을 한다.

영향:

- 목록/관심 화면은 현재 `bid_no`를 그대로 렌더링하므로 sample/sqlmodel 간 표기 차이가 생긴다.
- 상세/내부 식별은 `bid_id` 기준으로 유지하는 편이 안전하다.

현재 정책:

- 내부 식별과 라우팅은 `bid_id`를 사용한다.
- 화면 표시는 `display_bid_no`를 사용한다.
- `SqlModelBidRepository`는 `display_bid_no = bid_id`로 맞춰 sample/sqlmodel 간 표시를 통일한다.

### C. 상세 정보 밀도

- 샘플 데이터: `detail_rows`, `qualification`, `business_info`, `timeline`, `history`가 풍부하게 준비되어 있다.
- SQLModel 데이터: 현재는 `bids`, `bid_details`, `attachments` 중심으로 조회하고 나머지는 repository에서 규칙 기반 placeholder를 조립한다.

예시:

- `qualification_summary`: 샘플은 실제 문장, SQLModel은 `추후 세부 API 연동으로 보강 예정`
- `timeline`: 샘플은 사전규격/발주계획 포함, SQLModel은 입찰/개찰/계약 기본 골격 위주
- `history`: 샘플은 변경 이력 배열, SQLModel은 `last_synced_at` 기반 최소 이력만 생성

정리:

- drawer가 깨지지 않도록 구조는 맞추되, 내용 밀도는 아직 sample > sqlmodel 상태다.

### D. 본문 설명

- 샘플 데이터: `description_text`에 실제 요약 문장이 있다.
- SQLModel 데이터: `description_text`는 본문 요약 fallback 용도로 유지하고, 상세 링크는 `detail_url`로 분리했다.

영향:

- SQLModel 경로는 본문 요약과 상세 링크를 별도 필드로 전달한다.

현재 저장 정책:

- `BidDetail.raw_api_data`: G2B API 원본 JSON
- `BidDetail.crawl_data`: Playwright 수집 원본 payload
- `BidDetail.description_text`: 화면용 요약 텍스트
- `BidDetail.detail_url`: 원문 진입 링크
- `BidDetail.detail_hash`: crawl payload 변경 감지용 해시

후속 권장:

- Playwright 또는 후속 API 연동으로 `description_text`를 실제 본문 요약으로 채운다.

### E. 첨부파일

- 샘플 데이터: `source`가 `공고첨부`, `e발주` 등으로 구분된다.
- SQLModel 데이터: `source`로 `getBidPblancListInfoEorderAtchFileInfo`, `playwright_detail` 등 수집 경로를 구분한다.

정리:

- 첨부는 `(source, name, download_url)` 기준으로 upsert하고, `content_hash`는 `source|name|download_url` 기준으로 저장한다.

## 4. 현재 SQLModel 경로에서 의도적으로 단순화한 필드

- `domain_type`: 현재 고정값 `내자`
- `stage_label`: 현재 고정값 `입찰공고`
- `step_label`: 현재 고정값 `공고등록`
- `notice_type`: `last_changed_at` 존재 여부 기준 단순 판정
- `progress_label`: `closed_at` 비교 기반 단순 판정

## 5. mapper 관점 주의사항

- `build_bid_list_item_vm()`는 raw 데이터에 `status_variant`, `favorite`, `progress_label`이 이미 있다고 가정한다.
- `build_bid_drawer_vm()`는 `qualification`, `business_info`, `timeline`, `history`가 dict/list 구조로 준비되어 있다고 가정한다.
- 따라서 source별 차이는 mapper가 아니라 repository에서 먼저 흡수해야 한다.

## 6. 우선순위가 높은 후속 정리

1. SQLModel 경로의 `timeline/history`를 실제 데이터 기반으로 확장
2. 첨부파일 `source`와 세부 메타데이터 확장
