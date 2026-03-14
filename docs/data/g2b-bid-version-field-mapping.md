# G2B Bid Version Field Mapping

## 1. 목적

- 본 문서는 나라장터 입찰공고 API 응답에서 정정공고/취소공고/최신 유효 차수를 어떻게 판별할지 정리한다.
- 현재 UI와 테스트에서 먼저 정의한 버전 UX를 실제 OpenAPI 필드와 연결하기 위한 매핑 설계안이다.

## 2. 현재 상태 요약

현재 코드에서 이미 사용하는 필드:

- `bidNtceNo` -> `bids.bid_no`
- `bidNtceOrd` -> `bids.bid_seq`
- `chgDt` -> `bids.last_changed_at`
- `bidNtceNm` -> `bids.title`
- `bidNtceDtlUrl` -> `bid_details.detail_url`

현재 한계:

- 취소공고를 실제 API 필드로 판별하지 못한다.
- 정정공고도 사실상 `bid_seq > 최소차수`로만 추론한다.
- 변경이력 API를 아직 쓰지 않아 `무엇이 바뀌었는지`를 history/timeline에 실제 데이터로 넣지 못한다.

## 3. 우선 반영 대상 API

### 3.1 기본 목록 API

- `getBidPblancListInfoServc`
- `getBidPblancListInfoThng`
- `getBidPblancListInfoCnstwk`
- `getBidPblancListInfoFrgcpt`
- 필요 시 `getBidPblancListInfoEtc`

역할:

- 공고번호, 차수, 제목, 기관, 게시일시, 변경일시 같은 마스터 정보 적재
- 버전 체인의 기본 키 생성

### 3.2 변경이력 API

- `getBidPblancListInfoChgHstryServc`
- `getBidPblancListInfoChgHstryThng`
- `getBidPblancListInfoChgHstryCnstwk`

역할:

- 정정공고의 변경 항목과 전후값 저장
- timeline/history에 실제 변경 이벤트 반영

## 4. 필드 매핑 초안

### 4.1 기본 키와 버전 체인

| G2B 필드 | 내부 필드 | 용도 |
| --- | --- | --- |
| `bidNtceNo` | `bids.bid_no` | 공고 그룹 키 |
| `bidNtceOrd` | `bids.bid_seq` | 공고 차수 |
| `build_bid_id(bidNtceNo, bidNtceOrd)` | `bids.bid_id` | 단건 PK |
| `chgDt` | `bids.last_changed_at` | 변경 시각 |
| `rgstDt` 또는 `bidNtceDt` | `bids.posted_at` | 게시 시각 |

판정 규칙:

- 같은 `bidNtceNo` 아래 `bidNtceOrd`가 다르면 서로 다른 버전 row로 적재한다.
- `bidNtceOrd == 최소차수`이면 기본값은 `최초공고` 후보로 본다.
- `bidNtceOrd > 최소차수`이면 기본값은 `정정공고` 후보로 보되, 취소 필드가 있으면 우선 취소공고로 재분류한다.

### 4.2 버전 유형 분류

후보 정규화 필드:

- `notice_version_type`
  - `original`
  - `revision`
  - `cancellation`
  - `unknown`

권장 판정 순서:

1. API 응답에 취소 여부/취소 구분 필드가 있으면 `cancellation`
2. 그 외 `bidNtceOrd > 최소차수`면 `revision`
3. 그 외 최초 차수면 `original`
4. 확신할 수 없으면 `unknown`

중요:

- 실제 응답 샘플을 받아 취소 관련 필드명을 먼저 확정해야 한다.
- 현재 설계는 `bidNtceOrd`만으로 취소를 알 수 없다는 전제를 둔다.

### 4.3 최신 유효 차수 계산

후보 정규화 필드:

- `is_latest_version`
- `is_effective_version`

계산 규칙:

- 같은 `bid_no` 그룹에서 가장 큰 `bid_seq`를 `최신 차수` 후보로 본다.
- 그 차수가 `cancellation`이면 `is_effective_version = false`
- 같은 그룹에서 가장 큰 `bid_seq` 중 `is_effective_version = true`인 row를 `최신 유효 차수`로 본다.

### 4.4 변경이력 API 매핑

변경이력 API 공통 필드 후보:

- `bidNtceNo`
- `bidNtceOrd`
- `chgItemNm`
- 변경 전 값 필드
- 변경 후 값 필드
- 변경 시각 필드

권장 저장 대상:

- 신규 테이블 `bid_version_changes`
  - `bid_id`
  - `bid_no`
  - `bid_seq`
  - `change_item_name`
  - `before_value`
  - `after_value`
  - `changed_at`
  - `source_api_name`
  - `raw_data`

UI 활용:

- history: 변경 항목 요약
- timeline: `정정 공고 게시` 이벤트 + 대표 변경 1~3건 요약
- Drawer: `변경 항목` 표 또는 펼침 섹션

## 5. 실제 코드 반영 포인트

### 5.1 `app/services/g2b_bid_sync_service.py`

추가할 것:

- 기본 목록 응답에서 취소/정정 관련 후보 필드 추출
- `Bid` 정규화 필드에 값 저장
- `bid_detail.raw_api_data`에만 두지 말고 화면/조회용 필드로 승격

현재 참고 위치:

- `app/services/g2b_bid_sync_service.py:127`
- `app/services/g2b_bid_sync_service.py:141`
- `app/services/g2b_bid_sync_service.py:155`

### 5.2 `app/models/bid.py`

추가 검토 필드:

- `notice_version_type: Optional[str]`
- `is_latest_version: bool`
- `is_effective_version: bool`
- `parent_bid_id: Optional[str]`
- `version_reason: Optional[str]`

스키마 초안은 아래 문서를 기준으로 한다.

- `docs/data/data-model.md`

### 5.3 신규 변경이력 서비스

추가 후보:

- `app/services/g2b_bid_change_history_service.py`
- `app/sync_bid_change_history.py`
- 관련 client method in `app/clients/g2b_bid_public_info_client.py`

역할:

- `getBidPblancListInfoChgHstry*` 수집
- `bid_version_changes` 적재
- history/timeline 렌더링 데이터 제공

## 6. 매핑 우선순위

### Step 1. 응답 샘플 확보

- 실제 G2B 기본 목록 응답에서 취소/정정 관련 필드명 확인
- 실제 변경이력 API 응답 샘플 확보

### Step 2. 정규화 필드 추가

- `Bid`에 `notice_version_type`, `is_effective_version` 추가
- 기존 fixture 기반 로직을 실제 필드 우선 로직으로 치환

### Step 3. 변경이력 적재

- `getBidPblancListInfoChgHstry*` client/service/CLI 추가
- `bid_version_changes` 테이블 및 repository 조회 추가

### Step 4. UI 치환

- 현재 repository의 추론 로직을 정규화 필드 기반으로 전환
- history/timeline 문구를 실제 변경 항목 중심으로 바꾼다.

## 7. 현재 임시 규칙과 향후 치환 대상

현재 임시 규칙:

- `bid_seq == 최소차수` -> `최초공고`
- `bid_seq > 최소차수` -> `정정공고`
- 테스트 fixture의 `status == archived` -> `취소공고`

향후 치환 방향:

- `notice_version_type == cancellation` -> `취소공고`
- `notice_version_type == revision` -> `정정공고`
- `notice_version_type == original` -> `최초공고`
- `is_effective_version`으로 최신 유효 차수 계산

## 8. 남은 결정 사항

- 기본 목록 API 응답에 취소 여부를 직접 표현하는 필드가 있는지
- 취소공고를 별도 공고 유형으로 볼지, 버전 유형으로만 볼지
- `parent_bid_id`를 둘지, `bid_no + bid_seq` 계산으로 충분한지
- 변경이력 테이블을 별도 테이블로 둘지 `raw_api_data` 파생으로만 둘지

## 9. 권장 다음 작업

1. 실제 G2B 응답 샘플 3종 확보: 최초공고, 정정공고, 취소공고
2. `Bid` 모델에 버전 정규화 필드 추가 마이그레이션 설계
3. `getBidPblancListInfoChgHstry*` 연동 초안 구현
