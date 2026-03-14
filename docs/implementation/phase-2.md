# Phase 2 Implementation Plan

`PLAN.md`의 Phase 2를 실제 구현 단위로 세분화한 실행 문서다.

## 1. 목표

- PRD 기준 하이브리드 수집 기반을 구축한다.
- `입찰공고정보서비스` 1차 목록 수집 이후 상세 보강 API와 타임라인 API를 순차 연결한다.
- Playwright를 이용해 API로 채우기 어려운 상세 본문/첨부 정보를 보강한다.
- 실패 로그, 재시도, idempotent 갱신 규칙을 수집 파이프라인 전반에 적용한다.

## 2. 범위

포함:

- 입찰공고정보서비스 2차 보강 오퍼레이션 연결
- 계약과정통합공개, 업종 및 근거법규 데이터 적재 초안
- Playwright 수집기 초안과 세션/재시도 구조
- 첨부파일 메타데이터, 본문 텍스트, 연결 키 보강
- 수집 실패 로그/재시도/idempotent 정책 정비

제외:

- 고급 분석 화면 완성
- Excel 내보내기
- 다중 사용자 관심 공고 모델 전환
- PostgreSQL 운영 전환

## 3. 선행 기준 문서

- `docs/PRD.md`
- `PLAN.md`
- `docs/api/api-sync-strategy.md`
- `docs/architecture/system-architecture.md`
- `docs/data/data-model.md`
- `docs/implementation/phase-1.md`
- `docs/implementation/phase-2-checklist.md`

## 4. 작업 단위

### Track A. API 우선순위와 연결 키 확장

목표: 1차 목록 수집 이후 어떤 API를 어떤 키로 보강할지 코드와 문서 기준을 맞춘다.

체크리스트:

- [ ] Tier 1 API 중 Phase 2 우선 구현 범위를 확정
- [x] `bidNtceNo`, `bfSpecRgstNo`, `orderPlanNo`, `prcrmntReqNo` 저장 전략 정리
- [x] 기본 목록 -> 상세 보강 -> 타임라인 보강 순서를 CLI/서비스 구조에 반영
- [x] 관심 공고/변경 공고 선별 보강 대상 규칙 정의

산출물:

- 연결 키 메모 또는 helper
- API별 sync 우선순위 표
- CLI 실행 순서 정리

현재 결정:

- Phase 2 우선 범위는 `base_list -> detail_enrichment -> timeline_enrichment -> reference_enrichment` 순서를 따른다.
- base list는 기존 4개 목록 오퍼레이션(`Servc/Thng/Cnstwk/Frgcpt`)을 유지한다.
- detail enrichment는 `LicenseLimit`, `PrtcptPsblRgn`, `EorderAtchFileInfo`, `*PurchsObjPrdct`를 우선한다.
- timeline enrichment는 `계약과정통합공개서비스`를 별도 단계로 둔다.
- reference enrichment는 `업종 및 근거법규서비스`를 마지막 보강 계층으로 둔다.
- 연결 키는 `bidNtceNo`, `bfSpecRgstNo`, `orderPlanNo`, `orderPlanUntyNo`, `prcrmntReqNo`를 모두 후보로 보존한다.
- 상세 보강 대상은 `is_favorite`, 최근 변경, 신규 공고, `reviewing/favorite/submitted` 상태를 우선한다.

완료 기준:

- 어떤 공고에 어떤 API를 어떤 키로 호출할지 일관된 규칙이 정해진다.

### Track B. 입찰공고정보서비스 2차 보강

목표: 메인 상세 화면에 필요한 자격/지역/첨부/구매대상물품 보강 데이터를 적재한다.

체크리스트:

- [x] `getBidPblancListInfoLicenseLimit` 연동
- [x] `getBidPblancListInfoPrtcptPsblRgn` 연동
- [x] `getBidPblancListInfoEorderAtchFileInfo` 연동
- [x] 구매대상물품 계열 오퍼레이션 연동
- [x] 상세 보강 결과를 `qualification`, `attachments`, `business_info`로 연결

산출물:

- 상세 보강 service/repository 코드
- 필요 엔티티 또는 확장 테이블
- 보강 API 테스트 픽스처

완료 기준:

- 상세 Drawer의 자격/지역/첨부/품목 정보가 placeholder가 아니라 실제 적재 데이터로 일부 이상 교체된다.

현재 진행 메모:

- `G2BBidDetailEnrichmentService` 초안을 추가해 면허제한, 참가가능지역, e발주 첨부, 구매대상물품 오퍼레이션을 공고 단위로 저장할 수 있게 했다.
- `BidLicenseLimit`, `BidParticipationRegion`, `Attachment.source`를 도입해 상세 보강 결과를 구조화했다.
- `BidPurchaseItem`을 도입해 품목 코드/명칭/수량/인도조건을 저장한다.
- `SqlModelBidRepository`는 실제 저장된 면허/지역/첨부 source와 품목 정보를 우선 반영한다.
- `app/sync_bid_detail_enrichment.py`를 추가해 detail enrichment를 CLI로 실행하고 `SyncJobLog`에 성공/실패를 기록할 수 있게 했다.
- bid 지정이 없을 때는 `targeted` 모드로 동작하며, 관심 공고/최근 변경 공고/신규 공고/`reviewing|favorite|submitted` 상태를 우선 선별한다.
- detail enrichment 계열의 실제 호출 키는 `bidNtceNo` 중심으로 유지한다. 현재 구현은 `bid_no -> raw_api_data.bidNtceNo -> raw_api_data.untyNtceNo` 순으로 notice 계열 후보만 fallback 하며, `bfSpecRgstNo`/`orderPlanNo`/`prcrmntReqNo`는 이 계열 요청 파라미터로 직접 사용하지 않는다.

### Track C. 계약과정통합공개 + 결과 보강

목표: 입찰 이후 단계를 타임라인으로 연결할 최소 기반을 만든다.

체크리스트:

- [x] 계약과정통합공개 조회 서비스 초안 구현
- [x] `inqryDiv`별 연결 키 fallback 전략 구현
- [x] 낙찰/계약 결과용 최소 적재 구조 정의
- [x] 타임라인 snapshot 생성 규칙 초안 구현
- [x] 상세 화면 timeline/history 보강 연결

산출물:

- 통합 추적 service
- 타임라인 가공 규칙
- 결과/계약 관련 모델 또는 임시 저장 구조

현재 진행 메모:

- `G2BContractProcessClient`와 `G2BContractProcessService` 초안을 추가했다.
- lookup 순서는 `bidNtceNo -> bfSpecRgstNo -> orderPlanNo -> prcrmntReqNo` fallback을 따른다.
- `ContractProcessIntegration`, `TimelineStageSnapshot`을 도입해 낙찰/계약 최소 데이터를 저장한다.
- `SqlModelBidRepository`는 timeline snapshot이 있으면 상세 Drawer 타임라인에 우선 반영한다.
- `app/sync_contract_process.py`를 추가해 계약과정통합공개 보강을 CLI로 실행하고 `SyncJobLog`에 성공/실패를 기록할 수 있게 했다.
- 실제 수동 검증 후 업무구분별 오퍼레이션(`getCntrctProcssIntgOpenServc/Thng/Cnstwk/Frgcpt`)으로 수정했고, 용역 공고 1건에서 실제 응답 적재와 timeline snapshot 반영까지 확인했다.
- contract process 적재가 있으면 상세 Drawer `history`에도 낙찰업체/낙찰금액/계약번호/계약명/계약일자 이력을 우선 반영한다.
- `SqlModelPageRepository.list_results()`가 contract process 적재 데이터를 읽어 `/results` 화면에 낙찰업체/낙찰금액/계약일자를 노출한다.
- `app/sync_phase2_batch.py`를 추가해 detail enrichment -> contract process -> crawl을 한 번에 실행하는 상위 배치 CLI를 제공한다.
- 실제 수동 배치 검증에서 `R26BK01387837-000` 기준 `detail_items=0`, `contract_items=1`, `crawl_attachments=1` 결과와 `/operations`/상세 Drawer/`/results` 반영까지 확인했다.

완료 기준:

- 최소 일부 공고에서 입찰 -> 개찰/낙찰 -> 계약 흐름이 실제 데이터 기반으로 보강된다.

### Track D. Playwright 상세 수집기 초안

목표: API로 비는 상세 본문/첨부 메타데이터 영역을 브라우저 수집으로 보강한다.

체크리스트:

- [ ] Playwright 실행 진입점 정의
- [ ] persistent context/session 저장 위치 설계
- [ ] 로그인 필요 여부에 따른 실행 정책 정의
- [ ] 상세 본문, 첨부파일 목록, 링크 추출 selector 초안 작성
- [ ] DOM 변경/타임아웃/세션 만료 실패 처리 규칙 정의

산출물:

- Playwright crawler 모듈
- 브라우저 세션/설정 문서
- 실패 샘플 수집 규칙

현재 진행 메모:

- `G2BBidPageCrawler` 초안을 추가해 persistent context 기반 Chromium 세션 경로를 사용할 수 있게 했다.
- `G2BBidCrawlService`와 `app/sync_bid_crawl.py`를 추가해 공고 상세 URL 기준 크롤링 결과를 `bid_details.crawl_data`와 `Attachment(source=playwright_detail)`에 저장할 수 있게 했다.
- 현재 selector는 `#container`, `#content`, `main`, `body`와 다운로드 링크 패턴 기반의 초기 초안이다.
- 실제 G2B 상세 페이지 수동 검증 후 `[atch_file_nm]` + `onclick` 메타데이터 추출을 추가해 첨부 메타데이터(`bidCancelGuide.pdf`) 1건 저장까지 확인했다.
- 상세 Drawer는 `crawl_data.text_summary`가 있으면 `본문 요약`과 `크롤링 추출 본문` 영역에 우선 반영한다.
- `pytest tests/test_sync_bid_crawl_cli.py`로 `browser_timeout`, `browser_dom` 실패 분류와 운영 로그 포맷도 확인했다.

Track F 진행 메모:

- `app/services/sync_logging.py`를 추가해 API/브라우저 실패를 `failure_category`, `exception_type`, `status_code`, `retry_count`, `detail` 형식으로 표준화했다.
- 현재 분류 범주는 `api_http`, `api_timeout`, `browser_timeout`, `browser_session`, `browser_dom`, `browser_runtime`, `unexpected`다.
- `sync_bid_public_info`, `sync_bid_detail_enrichment`, `sync_contract_process`, `sync_bid_crawl`가 공통 실패 메시지 포맷을 사용한다.
- `app/services/retry.py`를 추가해 Phase 2 외부 호출에 공통 재시도/backoff 규칙을 적용했다.
- 현재 기본 정책은 API 계열 `max_attempts=3`, `backoff=1초 * 시도횟수`, 크롤링 계열 `max_attempts=2`, `backoff=1초 * 시도횟수`다.
- 재시도 대상은 API에서 `timeout`, `429`, `5xx`, 브라우저에서는 `TimeoutError`, `PlaywrightError`이며 그 외 예외는 즉시 종료한다.

완료 기준:

- 최소 1건 이상의 공고에서 본문 또는 첨부 목록을 브라우저 수집으로 저장할 수 있다.

### Track E. 첨부/본문 저장 구조 정리

목표: API/크롤링 양쪽에서 들어오는 상세 보강 데이터를 충돌 없이 저장한다.

체크리스트:

- [x] `BidDetail`에 API 요약/본문/상세 URL 구분 정책 확정
- [x] `Attachment`의 source/type/hash/dedup 규칙 정리
- [x] 첨부 중복 기준 `(bid_id, name, download_url)` 실제 적용 여부 검토
- [x] 본문/첨부 최종 수집 시각 기록 규칙 정리
- [x] 원본 JSON과 화면용 정규화 필드 분리 정책 점검

산출물:

- 모델 수정
- migration notes
- dedup/upsert 테스트

현재 진행 메모:

- API 첨부와 Playwright 첨부 모두 `(source, name, download_url)` 기준 upsert 흐름을 사용한다.
- `Attachment.content_hash`는 `source|name|download_url` 기준 SHA-256으로 저장한다.
- `BidDetail.detail_hash`는 `crawl_data` 전체 JSON 기준 SHA-256으로 저장해 본문 변경 감지를 돕는다.
- 재수집 시 source별 기존 첨부 중 새 응답에 없는 항목은 삭제하고, 있는 항목은 갱신한다.
- `BidDetail.raw_api_data`는 G2B API 원본 JSON, `BidDetail.crawl_data`는 Playwright 원본 payload로 분리한다.
- `BidDetail.detail_url`은 원문 링크, `BidDetail.description_text`는 화면용 요약, `BidDetail.detail_hash`는 변경 감지용 정규화 해시로 사용한다.
- `ContractProcessIntegration.raw_data`는 계약과정통합공개 원본 보관용, `award_company`, `award_amount`, `contract_no`, `contract_name`, `contract_date`는 화면/타임라인 정규화 필드로 사용한다.
- 화면/검색/타임라인은 정규화 필드를 우선 사용하고, 원본 JSON은 재파싱과 디버깅 기준 데이터로만 사용한다.
- 실제 수동 상세 보강 실행에서는 대상 공고 응답이 0건이었지만, CLI 동작과 운영 로그 적재는 정상 확인했다.

완료 기준:

- 재수집 시 첨부/본문 정보가 중복 누적되지 않고 최신 상태로 갱신된다.

### Track F. 실패 로그, 재시도, 운영성

목표: 외부 연동 실패를 운영 화면에서 추적 가능하게 만든다.

체크리스트:

- [ ] API/크롤링 공통 예외 분류 체계 정의
- [ ] 재시도 횟수, backoff, 실패 종료 조건 정의
- [ ] `sync_job_logs` 메시지 포맷 표준화
- [ ] 수동 재수집과 배치 수집의 로그 구분 기준 정의
- [ ] 실패 케이스 테스트와 수동 재현 절차 정리

산출물:

- 공통 sync error/helper
- 로그 포맷 규칙
- 실패 시나리오 테스트

완료 기준:

- 실패 원인과 재시도 결과를 `/operations`에서 판독할 수 있다.

## 5. 권장 구현 순서

1. Track A에서 API 범위와 연결 키 정책을 먼저 고정한다.
2. Track B에서 입찰공고정보서비스 2차 보강을 붙인다.
3. Track E에서 첨부/본문 저장 정책을 먼저 정리한다.
4. Track C에서 계약과정통합공개와 결과 보강을 연결한다.
5. Track D에서 Playwright 수집기를 붙인다.
6. Track F에서 실패/재시도/운영 로그를 다듬는다.

## 6. 작업 쪼개기

### Step 1. 상세 보강 API

- [x] 면허제한/참가가능지역/첨부/품목 API 클라이언트 추가
- [x] 대상 공고 선별 규칙 추가
- [x] 적재/업데이트 로직 추가

### Step 2. 타임라인 보강

- [x] 계약과정통합공개 클라이언트 추가
- [x] 연결 키 fallback 구현
- [x] timeline snapshot 생성

### Step 3. 브라우저 수집

- [ ] Playwright 설정/세션 저장
- [ ] 상세 본문 추출
- [ ] 첨부 메타데이터 추출

### Step 4. 운영성 보강

- [x] 실패 로그 표준화
- [ ] 재시도 정책 구현
- [x] `/operations` 표시값 보강

### Step 5. 검증

- [x] `pytest`
- [ ] 상세 보강 API 수동 실행
- [ ] 계약과정통합공개 수동 실행
- [ ] Playwright 수집 1건 이상 확인
- [ ] `/bids`, 상세 Drawer, `/operations` 확인

## 7. 위험 포인트

- API별 연결 키가 공고마다 비어 있을 수 있다.
- Playwright는 로그인/세션 만료/DOM 변경 영향을 크게 받는다.
- 상세 보강 API를 모든 공고에 호출하면 과호출 위험이 있다.
- 첨부 dedup 규칙이 약하면 재수집 시 중복이 빠르게 누적된다.

대응:

- 연결 키는 다단 fallback과 원본 보존을 기본으로 한다.
- 브라우저 수집은 신규/관심/변경 공고에 한정한다.
- 실패 샘플과 raw payload를 남겨 재현성을 확보한다.

## 8. Phase 2 완료 정의

- [ ] 상세 보강 API 데이터가 상세 Drawer에 실제로 노출된다.
- [ ] 계약과정통합공개 기반 타임라인 보강이 최소 1개 흐름에서 동작한다.
- [ ] Playwright로 본문 또는 첨부 메타데이터를 저장할 수 있다.
- [ ] 재수집 시 중복 없이 최신 상태 반영이 확인된다.
- [ ] 실패/재시도 정보가 운영 로그에서 확인된다.

## 9. 다음 문서 후보

- `docs/implementation/playwright-session-notes.md`
- `docs/implementation/sync-error-handling.md`
- `docs/implementation/timeline-integration-notes.md`
