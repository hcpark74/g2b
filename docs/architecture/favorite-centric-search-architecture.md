# Favorite-Centric Search Architecture

## 1. 목적

- 본 문서는 검색은 외부 API 중심으로 수행하고, 관심 공고만 내부 DB에 영속화하는 목표 아키텍처를 정리한다.
- 현재의 `전체 공고 선적재 후 DB 검색` 흐름을 `API 검색 -> 관심 등록 -> 관심 공고 동기화` 흐름으로 재구성하기 위한 기준 문서다.

## 2. 핵심 원칙

- 검색 결과의 1차 원천은 외부 G2B API다.
- 내부 DB의 1차 목적은 전체 공고 캐시가 아니라 `관심 공고 추적 저장소`다.
- 사용자가 관심 공고로 등록한 시점부터만 장기 추적, 상세 보강, 변경 감지, 운영 로그를 수행한다.
- 무거운 상세 수집은 사용자 상호작용과 분리해 백그라운드 job 또는 수동 sync로 처리한다.

## 3. 목표 사용자 흐름

### 3.1 검색

1. 사용자가 키워드, 기관명, 공고번호, 기간 조건으로 검색한다.
2. 서버는 외부 G2B API를 호출해 결과를 반환한다.
3. 검색 결과는 화면 렌더링용 응답으로만 사용하고 기본적으로 영구 저장하지 않는다.

### 3.2 관심 등록

1. 사용자가 검색 결과에서 특정 공고를 관심 공고로 등록한다.
2. 서버는 해당 공고의 최소 식별 정보와 원본 payload를 DB에 upsert 한다.
3. 동시에 후속 동기화 job을 예약하거나 백그라운드 task를 시작한다.

### 3.3 관심 공고 동기화

관심 등록 후 아래 데이터만 지속 추적한다.

- 기본 공고 정보 재조회
- 상세 보강 API
- 변경이력 API
- 계약과정통합공개 API
- 브라우저 크롤링 기반 첨부/본문 보강

## 4. 데이터 흐름

```text
[User Search]
    -> [Search API endpoint]
    -> [External G2B APIs]
    -> [Transient search result / short cache]
    -> [Rendered search result]

[Favorite click]
    -> [Favorite command endpoint]
    -> [Minimal bid upsert]
    -> [Sync job enqueue]
    -> [bids + bid_details + related tables + sync logs]

[Scheduled refresh]
    -> [favorite targets only]
    -> [public info/detail/change history/contract/crawl sync]
    -> [favorites screen + operations screen]
```

## 5. 책임 분리

### 5.1 검색 레이어

- 책임: 외부 API 검색, 응답 정규화, 검색 조건 검증, 짧은 캐시
- 비책임: 전체 검색 결과 영구 저장, 대량 장기 보관

### 5.2 관심 공고 레이어

- 책임: 관심 등록/해제, 내부 상태, 메모, 우선순위, 마지막 동기화 시각
- 검색 결과에 있던 공고를 추적 가능한 내부 엔터티로 승격하는 경계 역할을 맡는다.

### 5.3 동기화 레이어

- 책임: 관심 공고 대상 후속 API 호출, 변경 감지, 실패 로깅, 재시도
- 전체 시장 수집이 아니라 `선택된 공고의 깊이 있는 추적`에 집중한다.

### 5.4 운영 레이어

- 책임: `/favorites`, `/operations`, `/api/v1/health` 제공
- 범위: 관심 공고 기준 상태 판독, 최근 실패 job 판독, 수동 재실행

## 6. 저장 전략

### 6.1 DB에 저장하는 것

- 관심 등록된 공고의 최소 식별 정보
- 관심 공고의 최신 스냅샷과 버전 정보
- 관심 공고의 상세/첨부/계약/변경이력 보강 데이터
- sync job 로그, 실패 로그, 운영 상태 판독 정보

### 6.2 기본적으로 저장하지 않는 것

- 검색 결과 전체 목록
- 사용자가 한 번 보고 지나간 비관심 공고의 장기 이력
- 모든 공고의 상세/첨부/계약 데이터

### 6.3 선택적 캐시

- 최근 검색 결과는 짧은 TTL 캐시를 둘 수 있다.
- 캐시는 UX와 비용 최적화 목적이며 운영 기준 원본 저장소는 아니다.

## 7. 엔터티 방향

### 필수 엔터티

- `bids`: 관심 공고와 그 버전 스냅샷 저장
- `bid_details`: 상세 원문, raw payload, crawl 보강 저장
- `attachments`, `bid_version_changes`, `contract_process_integrations`: 관심 공고 관련 보강 데이터 저장
- `sync_job_logs`: 등록 직후 및 주기 sync 결과 저장

### 권장 신규 개념

- `favorite_targets` 또는 이에 준하는 개념을 둬서 `관심 등록 자체`와 `버전별 bid 스냅샷`을 분리한다.

권장 필드 예시:

- `tracking_id`
- `bid_no`
- `latest_bid_id`
- `tracking_status`
- `tracking_enabled`
- `memo`
- `created_at`
- `last_synced_at`

설계 의도:

- 하나의 공고번호에 정정/재공고가 생겨도 `tracking target`은 유지한다.
- 현재 추적 중인 최신 유효 차수는 `latest_bid_id`로 연결한다.

## 8. API/화면 방향

### 검색 화면

- `/` 또는 `/search`: 외부 API 검색 화면
- `/bids`: DB 결과 페이지가 아니라 검색 결과 표현 계층으로 재정의 가능
- 검색 결과 행 액션은 `상세 보기`, `관심 등록`, `원문 링크` 중심으로 둔다.

### 관심 공고 화면

- 내부 DB 기반으로 유지한다.
- 마감 임박, 변경 감지, 재확인 필요, sync 실패 중심으로 운영한다.

### 운영 화면

- 전체 공고 수집 현황보다 `관심 공고 동기화 현황` 중심으로 재정렬한다.
- job type도 `favorite_bid_refresh`, `favorite_bid_detail_enrichment`, `favorite_bid_crawl`처럼 관심 공고 기준 naming이 적합하다.

## 9. 백그라운드 작업 방향

관심 등록 직후 권장 순서:

1. 최소 bid upsert
2. public info refresh
3. detail enrichment
4. change history sync
5. contract process sync
6. crawl sync

운영 스케줄러 권장:

- 마감 임박 관심 공고: 짧은 주기 재동기화
- 일반 관심 공고: 일일 또는 반일 주기 재동기화
- 제출 완료/종료 공고: 긴 주기 또는 중단 정책 적용

## 10. 장점과 trade-off

장점:

- DB 크기와 운영 비용을 제어하기 쉽다.
- 사용자가 실제로 추적하는 공고에 집중할 수 있다.
- 상세 보강과 운영 로그를 관심 공고 기준으로 설명하기 쉽다.

trade-off:

- 검색 시 외부 API 응답속도와 장애 영향을 직접 받는다.
- 검색 결과와 내부 관심 데이터의 일시적인 불일치가 생길 수 있다.
- 검색 캐시, 호출 제한, 중복 요청 제어가 필요하다.

## 11. 단계별 전환 계획

### Phase A. 검색/영속화 경계 분리

- `/bids` 검색을 DB 조회에서 외부 API 검색으로 분리
- 검색 결과 DTO와 내부 DB 엔터티를 분리
- 관심 등록 endpoint에서만 DB upsert 수행

### Phase B. 관심 공고 중심 sync 재배치

- 기존 대량 sync를 관심 공고 대상 sync로 축소
- 등록 직후 background sync 연결
- `/operations` 필터와 문구를 관심 공고 추적 관점으로 재정리

### Phase C. 보존/중단 정책 도입

- 종료 공고, 장기 미관심 공고, 실패 반복 공고의 sync 정책 정리
- TTL 캐시, 재시도, backoff, 알림 기준 확정

## 12. 비목표

- 전체 나라장터 공고의 완전한 로컬 미러링
- 검색 시점마다 모든 상세/첨부 데이터를 즉시 수집
- 비관심 공고의 장기 히스토리 완전 보존

## 13. 결정 문장

- 이 시스템의 검색은 외부 API 중심으로 수행한다.
- 이 시스템의 내부 DB는 관심 공고 추적과 운영 복구를 위한 저장소로 사용한다.
- 동기화의 기본 대상은 전체 공고가 아니라 관심 공고다.
