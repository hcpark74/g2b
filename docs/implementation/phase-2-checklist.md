# Phase 2 Checklist

Phase 2 외부 수집 확장을 실행/검증하기 위한 체크리스트다.

## 1. API 범위 확정

- [x] Phase 2 대상 API 우선순위 확정
- [x] 연결 키(`bidNtceNo`, `bfSpecRgstNo`, `orderPlanNo`, `prcrmntReqNo`) 저장 규칙 확정
- [x] 기본 목록 -> 상세 보강 -> 타임라인 보강 호출 순서 확정

## 2. 입찰공고정보서비스 2차 보강

- [x] 면허제한 API 연동
- [x] 참가가능지역 API 연동
- [x] e발주 첨부 API 연동
- [x] 구매대상물품 API 연동
- [x] 상세 Drawer 반영 확인

## 3. 계약과정통합공개/결과 보강

- [x] 계약과정통합공개 조회 구현
- [x] `inqryDiv` fallback 규칙 구현
- [x] 낙찰/계약 최소 적재 구조 구현
- [x] timeline snapshot 반영 확인

## 4. Playwright 수집

- [x] Playwright 실행 진입점 구현
- [x] 세션 저장 위치/정책 정리
- [x] 상세 본문 추출 구현
- [x] 첨부 메타데이터 추출 구현
- [x] 타임아웃/DOM 변경 실패 처리 확인

## 5. 저장/중복 방지

- [x] 본문 요약/상세 URL/원문 구분 확인
- [x] 첨부 dedup 규칙 적용 확인
- [x] 재수집 시 중복 없이 upsert 확인
- [x] 최종 수집 시각 갱신 확인
- [x] 원본 JSON과 화면용 정규화 필드 분리 정책 점검

## 6. 운영성

- [x] 실패 로그 포맷 표준화
- [x] 재시도 횟수 및 종료 조건 반영
- [x] `/operations`에서 실패/재시도 정보 확인
- [x] 수동 재수집과 배치 로그 구분 확인
- [x] API/브라우저 공통 실패 분류 체계 반영
- [x] 공통 실패 메시지 포맷 테스트 반영
- [x] 공통 retry/backoff 정책 테스트 반영

## 7. 검증

- [x] `pytest`
- [x] detail enrichment CLI 성공/실패 로그 테스트
- [x] contract process CLI 성공/실패 로그 테스트
- [x] 상세 보강 API 수동 실행
- [x] 계약과정통합공개 수동 실행
- [x] Playwright 수집 1건 이상 성공
- [x] `/bids`, 상세 Drawer, `/operations` 수동 확인
- [x] contract process 적재 시 history 반영 테스트
- [x] contract process 적재 시 낙찰금액/계약일자 history 반영 테스트
- [x] `/results` 화면 contract process 데이터 반영 테스트
- [x] Playwright crawl service/CLI 성공·실패 테스트
- [x] crawl_data 기반 상세 Drawer 본문 반영 테스트
- [x] Phase 2 상위 batch CLI 성공·실패 테스트
- [x] Phase 2 상위 batch CLI 수동 실행

## 8. 완료 기준

- [x] 상세 보강 데이터가 실제 화면에 노출된다.
- [x] 타임라인 보강이 최소 1개 흐름에서 동작한다.
- [x] 브라우저 수집 결과가 저장된다.
- [x] 재수집 시 중복 없이 최신 상태가 유지된다.
- [x] 실패/재시도 정보가 운영 로그에서 확인된다.

## 9. 운영 예시 명령

기본 targeted 모드:

```bash
python -m app.sync_bid_detail_enrichment --operation getBidPblancListInfoLicenseLimit --operation getBidPblancListInfoPrtcptPsblRgn --operation getBidPblancListInfoEorderAtchFileInfo --operation getBidPblancListInfoThngPurchsObjPrdct --operation getBidPblancListInfoServcPurchsObjPrdct --recent-days 7
```

특정 공고만 보강:

```bash
python -m app.sync_bid_detail_enrichment --bid-id R26BK01386273-000 --operation getBidPblancListInfoLicenseLimit --operation getBidPblancListInfoEorderAtchFileInfo
```

전체 공고 강제 보강:

```bash
python -m app.sync_bid_detail_enrichment --selection-mode all --operation getBidPblancListInfoLicenseLimit --operation getBidPblancListInfoPrtcptPsblRgn
```

계약과정통합공개 보강:

```bash
python -m app.sync_contract_process --bid-id R26BK01386273-000
```

Phase 2 상위 배치:

```bash
python -m app.sync_phase2_batch --selection-mode targeted --recent-days 7
```

Admin Sync API 예시:

```bash
curl -X POST "http://127.0.0.1:8000/admin/sync/phase2-batch" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: dev-admin-token" \
  -d '{"selection_mode":"targeted","recent_days":7}'
```

운영 로그 조회 예시:

```bash
curl -X GET "http://127.0.0.1:8000/admin/operations?job_type=phase2_batch_sync" \
  -H "X-Admin-Token: dev-admin-token"
```

## 10. 2026-03-14 계약과정통합공개 실행 메모

- [x] 검증 DB: `sqlite:///./manual-phase2-contract.db`
- [x] 선행 목록 적재: `python -m app.sync_bid_public_info --begin 202603120000 --end 202603132359 --operation getBidPblancListInfoServc --rows 20`
- [x] 실제 실행: `python -m app.sync_contract_process --bid-id R26BK01387837-000`
- [x] 실행 결과: `contract_process_sync` 실패 로그 기록 확인
- [x] 실패 내용: `HTTPStatusError 404 Not Found`
- [x] `/operations`에서 실패 로그 확인
- [x] `/partials/bids/R26BK01387837-000/drawer`는 기존 placeholder timeline 유지 확인
- [x] 클라이언트 경로 수정 후 실제 응답 적재 성공
- [x] 성공 로그 확인: `processed 1 bids, fetched 1 items`
- [x] 적재 결과 확인: `contract_process_integrations=1`, `timeline_stage_snapshots=3`
- [x] `/operations`에서 성공 로그 확인
- [x] 상세 Drawer에서 timeline snapshot 반영 확인

## 11. 2026-03-14 Playwright 실행 메모

- [x] `python -m pip install playwright`
- [x] `python -m playwright install chromium`
- [x] 실제 실행: `python -m app.sync_bid_crawl --bid-id R26BK01387837-000`
- [x] `bid_details.crawl_data` 저장 확인
- [x] 크롤링 첨부 메타데이터 1건 저장 확인: `bidCancelGuide.pdf`
- [x] `/partials/bids/R26BK01387837-000/drawer`에서 첨부 표시 확인
- [x] `bid_page_crawl` 성공 로그 확인: `processed 1 bids, stored 1 attachments`

## 12. 2026-03-14 Phase 2 배치 실행 메모

- [x] 검증 DB: `sqlite:///./manual-phase2-batch.db`
- [x] 선행 목록 적재: `python -m app.sync_bid_public_info --begin 202603120000 --end 202603132359 --operation getBidPblancListInfoServc --rows 20`
- [x] 실제 실행: `python -m app.sync_phase2_batch --bid-id R26BK01387837-000`
- [x] 배치 로그 확인: `selection_mode=targeted processed 1 bids detail_items=0 change_history_items=0 contract_items=1 crawl_attachments=1`
- [x] 적재 확인: `crawl_data`, `detail_hash`, `attachments=1`, `contract_process_integrations=1`, `timeline_stage_snapshots=3`
- [x] `/operations`에서 `phase2_batch_sync` 확인
- [x] `/partials/bids/R26BK01387837-000/drawer`에서 크롤링 첨부/본문 유지 확인
- [x] `/results`에서 계약과정통합공개 결과 반영 확인
- [x] Phase 2 배치에 `bid_change_history_sync` 단계 포함 반영

## 13. 2026-03-14 상세 보강/실패 처리 메모

- [x] 실제 실행: `python -m app.sync_bid_detail_enrichment --bid-id R26BK01387837-000 --operation getBidPblancListInfoLicenseLimit --operation getBidPblancListInfoPrtcptPsblRgn --operation getBidPblancListInfoEorderAtchFileInfo`
- [x] 실행 로그 확인: `processed 1 bids, fetched 0 items`
- [x] 실제 응답은 0건이지만 수동 실행/로그 적재 확인
- [x] `pytest tests/test_sync_bid_crawl_cli.py`로 `browser_timeout`, `browser_dom` 실패 분류 확인

## 14. 2026-03-14 Phase 2 재검증 메모

- [x] 재검증 DB: `sqlite:///./manual-phase2-rerun.db`
- [x] 선행 목록 적재: `python -m app.sync_bid_public_info --begin 202603120000 --end 202603132359 --operation getBidPblancListInfoServc --rows 20`
- [x] 상세 보강 재실행: `python -m app.sync_bid_detail_enrichment --bid-id R26BK01387837-000 --operation getBidPblancListInfoLicenseLimit --operation getBidPblancListInfoPrtcptPsblRgn --operation getBidPblancListInfoEorderAtchFileInfo`
- [x] 상세 보강 로그 재확인: `processed 1 bids, fetched 0 items`
- [x] 계약과정통합공개 재실행: `python -m app.sync_contract_process --bid-id R26BK01387837-000`
- [x] 계약과정통합공개 로그 재확인: `processed 1 bids, fetched 1 items`
- [x] Playwright 재실행: `python -m app.sync_bid_crawl --bid-id R26BK01387837-000`
- [x] Playwright 로그 재확인: `processed 1 bids, stored 1 attachments`
- [x] Phase 2 배치 재실행: `python -m app.sync_phase2_batch --bid-id R26BK01387837-000`
- [x] 배치 로그 재확인: `selection_mode=targeted processed 1 bids detail_items=0 change_history_items=0 contract_items=1 crawl_attachments=1 reference_items=0`
- [x] 적재 재확인: `contract_process_integrations=1`, `timeline_stage_snapshots=3`, `attachments_total=1`, `attachments_playwright=1`
- [x] `bid_details.detail_hash` 및 `crawl_data.text_summary` 저장 재확인
- [x] 크롤링 첨부 재확인: `bidCancelGuide.pdf`
- [x] `TestClient` 기준 `/partials/bids/R26BK01387837-000/drawer` 응답 `200` 및 본문/첨부 반영 확인
- [x] `TestClient` 기준 `/results` 응답 `200` 및 대상 공고 반영 확인
- [x] `TestClient` 기준 `/operations` 응답 `200` 및 `phase2_batch_sync`, `contract_process_sync`, `bid_page_crawl` 로그 노출 확인

## 15. 2026-03-14 변경이력 배치 연동 메모

- [x] `python -m app.sync_bid_change_history --bid-id R26BK10000002-000` CLI 초안 추가
- [x] `bid_version_changes` 모델/테이블 초안 추가
- [x] `sync_phase2_batch`에 change history sync 단계 추가
- [x] phase2 batch 로그에 `change_history_items` 카운트 반영
- [x] admin phase2 batch API 응답에 `change_history_items` 반영
- [x] `bid_version_changes` 기반 Drawer history/timeline 반영 테스트 추가
