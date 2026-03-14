# Phase 1 Implementation Plan

`PLAN.md`의 Phase 1을 실제 구현 단위로 세분화한 실행 문서다.

## 1. 목표

- 샘플 데이터 기반 화면을 SQLite/SQLModel 기반 실제 조회 흐름으로 전환한다.
- 메인 리스트, 상세 보기, 운영 로그를 하나의 저장소 경로로 연결한다.
- sync/seed 결과가 화면에 일관되게 반영되는 MVP 운영 루프를 완성한다.

## 2. 범위

포함:

- 핵심 엔티티와 SQLModel 매핑 정리
- repository/service 연결 전환
- 메인 화면과 상세 화면 DB 연동
- 운영 로그 조회 연결
- 핵심 테스트와 수동 검증 절차 추가

제외:

- Playwright 크롤링 본격 구현
- 계약과정통합공개/업종 API 확장
- Excel 내보내기
- 사전 탐색/사후 분석 고도화

## 3. 선행 기준 문서

- `docs/PRD.md`
- `PLAN.md`
- `docs/data/data-model.md`
- `docs/architecture/code-architecture.md`
- `docs/api/internal-bids.md`

## 4. 작업 단위

### Track A. 데이터 모델 정리

목표: 현재 sync/seed와 화면 조회에 필요한 최소 엔티티를 SQLModel로 고정한다.

체크리스트:

- [x] `bids`, `bid_details`, `attachments`, `sync_jobs` 또는 현재 사용 중인 로그 테이블 명칭을 기준으로 실제 모델 후보 확정
- [x] 공통 timestamp, 상태값, PK/UK 규칙 문서와 코드 간 차이 확인
- [x] `bid_id`, `bid_no`, `bid_seq` 식별 규칙을 코드 상수 또는 helper로 통일
- [x] JSON 원본 저장 컬럼의 타입/직렬화 규칙 확정
- [x] 인덱스 우선순위 정의: 메인 리스트, 상세 조회, 최근 동기화 이력 중심

산출물:

- `app/models/` 하위 SQLModel 엔티티
- 필요 시 공통 enum/helper
- 문서와 실제 모델 간 차이 메모

완료 기준:

- 주요 엔티티가 SQLModel로 정의되어 있고 초기화 시 테이블 생성이 가능하다.

인덱스 우선순위 메모:

- `bids.bid_id`: 상세 조회와 내부 식별자의 최우선 PK
- `bids.status`, `bids.posted_at`, `bids.closed_at`, `bids.is_favorite`: 메인 리스트/관심 목록/상태 필터 우선
- `bids.bid_no`, `bids.bid_seq`: 외부 공고 식별과 upsert 정합성 우선
- `bids.notice_org`, `bids.demand_org`, `bids.budget_amount`: 조직/예산 중심 탐색 보조
- `attachments.bid_id`: 상세 Drawer 첨부파일 조회 우선
- `bid_details.bid_id`: 상세 본문 단건 조회 우선, `detail_hash`와 `collected_at`은 변경 감지 보조
- `sync_job_logs.job_type`, `sync_job_logs.status`, `sync_job_logs.target`: `/operations` 목록과 필터 우선

### Track B. Repository 전환

목표: 샘플 저장소를 대체할 실제 DB 조회 경로를 만든다.

체크리스트:

- [x] 기존 `bid_repository.py`, `page_repository.py` 인터페이스 확인
- [x] `SqlModelBidRepository` 초안 구현
- [x] 메인 리스트용 조회 조건: 검색어, 상태, 정렬, 페이징 지원 범위 정의
- [x] 상세 조회용 `bids + bid_details + attachments` 조합 조회 구현
- [x] 운영 로그 조회용 repository 구현 또는 기존 경로 정리
- [x] `BID_DATA_BACKEND=auto|sample|sqlmodel` 분기 기준을 서비스 진입점에서 일관화

산출물:

- `app/repositories/` 하위 SQLModel 구현체
- 저장소 선택 팩토리 또는 의존성 주입 정리

완료 기준:

- 서비스 계층이 샘플/실DB 저장소를 동일 인터페이스로 호출할 수 있다.

### Track C. Service와 Mapper 정합화

목표: 화면 계층이 데이터 소스 변경을 의식하지 않도록 조립 계층을 정리한다.

체크리스트:

- [x] `bid_query_service.py`, `page_query_service.py`의 데이터 소스 의존 코드 점검
- [x] DB 경로에서 누락되는 필드와 샘플 데이터 필드 차이 정리
- [x] 메인 리스트 view-model에 필요한 최소 필드 세트 확정
- [x] 상세 Drawer view-model에 필요한 첨부파일, 본문, 메타데이터 매핑 확정
- [x] 운영 로그 화면 mapper가 sync 결과를 읽을 수 있도록 정리

산출물:

- service 계층 수정
- mapper/view-model 보강
- 샘플 데이터와 SQLModel 데이터 간 매핑 차이 표

관련 문서:

- `docs/implementation/repository-migration-notes.md`

완료 기준:

- 같은 템플릿이 샘플 데이터와 SQLModel 데이터 모두로 렌더링된다.

### Track D. 화면 연결

목표: 메인 사용자 흐름을 실제 데이터로 시연 가능하게 만든다.

체크리스트:

- [x] 메인 리스트 라우트가 DB 데이터 기준으로 응답하는지 확인
- [x] 행 선택 시 상세 Drawer 또는 상세 partial이 DB 조회를 사용하도록 연결
- [x] `/operations` 또는 운영 로그 화면이 sync 결과를 노출하도록 연결
- [x] 데이터가 없을 때 empty state와 sample fallback 정책 명확화
- [ ] seed 직후와 sync 직후 화면 반영 흐름 수동 확인

산출물:

- 라우트/의존성 수정
- 템플릿에 필요한 최소 필드 보강

완료 기준:

- 실제 DB에 적재된 공고가 메인 리스트와 상세 화면에서 확인된다.

### Track E. 테스트와 검증

목표: 전환 작업이 회귀 없이 유지되도록 최소 품질 게이트를 만든다.

체크리스트:

- [x] repository 단위 테스트 추가
- [x] service 단위 테스트 추가
- [x] mapper/view-model 테스트 보강
- [x] 메인 라우트와 상세 응답 통합 테스트 추가
- [x] seed/sync 후 조회 가능한지 검증하는 smoke test 또는 수동 절차 정리

산출물:

- `tests/` 하위 테스트 코드
- 수동 검증 체크리스트

관련 문서:

- `docs/implementation/testing-checklist.md`

완료 기준:

- 핵심 테스트가 통과하고, 수동 시나리오로 MVP 흐름을 재현할 수 있다.

## 5. 권장 구현 순서

1. Track A에서 모델과 식별 규칙을 먼저 고정한다.
2. Track B에서 `SqlModelBidRepository`와 운영 로그 조회 경로를 구현한다.
3. Track C에서 service/mapper를 DB 경로에 맞춘다.
4. Track D에서 메인 리스트, 상세, 운영 로그를 실제 데이터로 연결한다.
5. Track E에서 테스트와 수동 검증 절차를 마무리한다.

## 6. 작업 쪼개기

### Step 1. 모델 스캐폴딩

- [x] 현재 `app/models/` 구조 확인
- [x] 공통 base/helper가 필요한지 결정
- [x] `Bid`, `BidDetail`, `Attachment`, `SyncJobLog` 또는 대응 모델 생성

### Step 2. DB 조회 최소 경로 확보

- [x] 리스트 조회 쿼리 구현
- [x] 단건 상세 조회 쿼리 구현
- [x] 최근 sync 이력 조회 쿼리 구현

### Step 3. 서비스 연결

- [x] repository 선택 로직 정리
- [x] 메인 화면 서비스 DB 연결
- [x] 상세 화면 서비스 DB 연결
- [x] 운영 로그 서비스 DB 연결

### Step 4. 화면 회귀 정리

- [x] 템플릿 필드 누락 확인
- [x] empty state/오류 상태 확인
- [x] sample backend와 sqlmodel backend 결과 비교

### Step 5. 검증

- [x] `pytest`
- [x] `python -m app.seed_bids`
- [x] `python -m app.sync_bid_public_info --begin ... --end ...`
- [x] 메인 화면 진입
- [x] 상세 Drawer 확인
- [x] `/operations` 확인

## 7. 위험 포인트

- 샘플 데이터와 DB 스키마 필드명이 다를 수 있다.
- 기존 템플릿이 샘플 전용 필드 구조에 의존할 수 있다.
- sync 로그 테이블 명칭이 문서와 실제 코드에서 다를 수 있다.
- `auto` 모드 fallback 규칙이 불명확하면 디버깅이 어려워진다.

대응:

- mapper에서 화면용 필드 계약을 먼저 고정한다.
- repository는 원본 모델이 아니라 화면 요구사항 중심 DTO를 반환해도 된다.
- 로그/상태 관련 명칭은 코드 기준으로 통일하고 문서를 즉시 갱신한다.

## 8. Phase 1 완료 정의

- [x] `BID_DATA_BACKEND=sqlmodel`에서 메인 리스트가 정상 렌더링된다.
- [x] 공고 상세 정보와 첨부파일 정보가 실제 DB 기준으로 조회된다.
- [x] 최근 sync 결과가 운영 화면 또는 대응 조회 경로에 노출된다.
- [x] 샘플 데이터 없이도 기본 시연이 가능하다.
- [x] 핵심 테스트와 수동 검증 절차가 정리되어 있다.

## 9. 다음 문서 후보

- `docs/implementation/phase-2.md`
- `docs/implementation/testing-checklist.md`
- `docs/implementation/repository-migration-notes.md`
