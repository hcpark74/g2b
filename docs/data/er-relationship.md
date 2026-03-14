# ER Relationship

## 1. 목적

- 본 문서는 G2B 입찰 관리 시스템의 핵심 엔터티와 관계를 ER 관점에서 정리한다.
- 기준 문서는 `docs/data/data-model.md`, `docs/architecture/system-architecture.md`, `docs/api/api-sync-strategy.md`를 따른다.

## 2. 핵심 설계 원칙

- 내부 중심 엔터티는 `bids`다.
- 대부분의 상세/보강 데이터는 `bid_id` 또는 `bid_ntce_no + bid_ntce_ord`로 연결된다.
- 외부 API 원문 보존과 정규화 테이블을 병행한다.
- 사전규격/발주계획/조달요청/계약과정 데이터는 공고 마스터를 보강하는 연결 레이어로 본다.

## 3. 최상위 엔터티 구조

```text
bids
 |- bid_details
 |- attachments
 |- favorites
 |- sync_jobs
 |- timeline_logs
 |- bid_license_limits
 |- bid_participation_regions
 |- bid_purchase_items
 |- bid_base_amounts
 |- bid_change_histories
 |- bid_eorder_attachments
 |- contract_process_integrations
     |- contract_process_awards
     |- contract_process_contracts
     |- timeline_stage_snapshots
```

기준정보 레이어는 별도로 유지한다.

```text
industry_base_law_rules
 |- industry_inclusion_licenses
```

## 4. 엔터티별 관계

### `bids`

- 역할: 시스템의 운영 중심 마스터
- 주요 키:
  - `bid_id`
  - `bid_no`
  - `bid_seq`
  - `bid_ntce_no`에 대응되는 외부 식별값

관계:

- `1:1` `bid_details`
- `1:N` `attachments`
- `1:N` `favorites`
- `1:N` `sync_jobs`
- `1:N` `timeline_logs`
- `1:N` `bid_license_limits`
- `1:N` `bid_participation_regions`
- `1:N` `bid_purchase_items`
- `1:N` `bid_base_amounts`
- `1:N` `bid_change_histories`
- `1:N` `bid_eorder_attachments`
- `1:N` `contract_process_integrations`

### `bid_details`

- 역할: 공고 상세 본문/원본 데이터 저장
- 관계:
  - `N:1` -> `bids`

### `attachments`

- 역할: 일반 첨부파일 메타데이터
- 관계:
  - `N:1` -> `bids`

### `bid_license_limits`

- 역할: 면허제한/허용업종 원문 저장
- 관계:
  - `N:1` -> `bids`

설계 메모:

- 추후 `permsn_indstryty_list_raw`를 더 세밀하게 파싱하면 하위 허용업종 테이블이 추가될 수 있다.

### `bid_participation_regions`

- 역할: 참가가능지역 목록
- 관계:
  - `N:1` -> `bids`

### `bid_purchase_items`

- 역할: 물품/용역/외자의 구매대상 품목 상세
- 관계:
  - `N:1` -> `bids`

설계 메모:

- 하나의 공고에 여러 품목이 연결될 수 있으므로 `1:N` 구조가 자연스럽다.

### `bid_base_amounts`

- 역할: 기초금액, 예비가격 범위, 보험료/A값 상세
- 관계:
  - `N:1` -> `bids`

설계 메모:

- 실무적으로는 공고당 최신 1건만 중요할 수 있지만, 이력 관리를 위해 `1:N`으로 두는 것이 안전하다.

### `bid_change_histories`

- 역할: 공고 변경 전후값 기록
- 관계:
  - `N:1` -> `bids`

설계 메모:

- 운영 알림과 이력 표시용으로 중요하다.

### `bid_eorder_attachments`

- 역할: e발주 첨부파일 및 혁신장터 최종 제안요청서 첨부파일
- 관계:
  - `N:1` -> `bids`

### `contract_process_integrations`

- 역할: 계약과정통합공개 원본 허브
- 관계:
  - `N:1` -> `bids`
  - `1:N` -> `contract_process_awards`
  - `1:N` -> `contract_process_contracts`
  - `1:N` -> `timeline_stage_snapshots`

설계 메모:

- `bid_id`가 없더라도 `bid_ntce_no`, `bf_spec_rgst_no`, `order_plan_no`, `prcrmnt_req_no`를 통해 먼저 적재될 수 있다.

### `contract_process_awards`

- 역할: 낙찰자정보목록 정규화
- 관계:
  - `N:1` -> `contract_process_integrations`

### `contract_process_contracts`

- 역할: 계약정보목록 정규화
- 관계:
  - `N:1` -> `contract_process_integrations`

### `timeline_stage_snapshots`

- 역할: 화면용 타임라인 읽기 모델
- 관계:
  - `N:1` -> `bids`
  - `N:1` -> `contract_process_integrations`

### `industry_base_law_rules`

- 역할: 업종/근거법규 기준정보 마스터
- 관계:
  - `1:N` -> `industry_inclusion_licenses`

설계 메모:

- 현재는 `bids`와 직접 FK로 연결하지 않고, 업종코드/참가자격 해석 로직에서 간접 참조한다.

## 5. 관계 유형 요약

### 운영 마스터 기준

| Parent | Child | 관계 |
|---|---|---|
| `bids` | `bid_details` | `1:1` 또는 `1:N(이력형)` |
| `bids` | `attachments` | `1:N` |
| `bids` | `bid_license_limits` | `1:N` |
| `bids` | `bid_participation_regions` | `1:N` |
| `bids` | `bid_purchase_items` | `1:N` |
| `bids` | `bid_base_amounts` | `1:N` |
| `bids` | `bid_change_histories` | `1:N` |
| `bids` | `bid_eorder_attachments` | `1:N` |
| `bids` | `contract_process_integrations` | `1:N` |

### 계약과정 보강 기준

| Parent | Child | 관계 |
|---|---|---|
| `contract_process_integrations` | `contract_process_awards` | `1:N` |
| `contract_process_integrations` | `contract_process_contracts` | `1:N` |
| `contract_process_integrations` | `timeline_stage_snapshots` | `1:N` |

### 기준정보 기준

| Parent | Child | 관계 |
|---|---|---|
| `industry_base_law_rules` | `industry_inclusion_licenses` | `1:N` |

## 6. 연결 키 설계

### 내부 기본 키

- `bid_id`
- `contract_process_id`
- `industry_rule_id`

### 외부 연결 키

- `bid_ntce_no`
- `bid_ntce_ord`
- `bf_spec_rgst_no`
- `order_plan_no`
- `order_plan_unty_no`
- `prcrmnt_req_no`
- `unty_ntce_no`

### 설계 원칙

- 가능하면 `bid_id`로 직접 연결한다.
- 직접 연결이 어려운 외부 데이터는 보조 연결 키를 함께 저장한다.
- 외부 키만 존재하는 선행 적재를 허용한 뒤 후속 매칭으로 `bid_id`를 채우는 구조가 안전하다.

## 7. 추천 ER 해석

### 가장 중요한 중심축

```text
bids
  -> bid_details
  -> bid_change_histories
  -> bid_license_limits
  -> bid_purchase_items
  -> contract_process_integrations
```

이 의미는 다음과 같다.

- 공고 마스터를 먼저 만든다.
- 공고 상세와 변경이력을 붙인다.
- 자격/품목을 붙인다.
- 마지막으로 결과/계약/타임라인을 붙인다.

## 8. 향후 확장 포인트

- `bid_license_limits` 하위 허용업종 정규화 테이블
- `bid_purchase_items`의 세부품명 코드 마스터 연결
- `bids`와 `industry_base_law_rules` 간 간접 매핑 테이블
- `notifications`, `comments`, `audit_logs` 추가

## 9. 결론

- ER 구조의 중심은 `bids`다.
- `BidPublicInfoService`는 이 `bids`를 채우는 운영 중심 원천이다.
- `계약과정통합공개서비스`는 결과/계약/타임라인 보강 허브다.
- 기준정보와 결과정보는 모두 `bids`를 기준으로 방사형으로 붙는 구조가 가장 안정적이다.
