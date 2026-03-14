# Phase 1 Testing Checklist

Phase 1 범위에서 수동으로 확인할 항목을 정리한 체크리스트다.

## 1. 사전 준비

- [ ] 가상환경이 활성화되어 있다.
- [ ] 필요한 환경 변수가 설정되어 있다. 최소: `DATABASE_URL`, `BID_DATA_BACKEND`
- [ ] 테스트용 DB 파일 또는 빈 SQLite 경로를 준비했다.

권장 예시:

```bash
set DATABASE_URL=sqlite:///./g2b-phase1.db
set BID_DATA_BACKEND=sqlmodel
```

## 2. 자동 테스트

- [x] `pytest`
- [x] 주요 회귀 테스트를 다시 확인한다.

권장 예시:

```bash
pytest tests/test_model_helpers.py tests/test_bid_query_service.py tests/test_sqlmodel_bid_repository.py tests/test_sqlmodel_operation_repository.py tests/test_pages_sqlmodel.py tests/test_g2b_bid_sync_service.py
```

기대 결과:

- [x] 모든 테스트가 통과한다.

## 3. 시드 데이터 검증

- [x] `python -m app.seed_bids`
- [x] 시드 완료 로그 또는 출력 건수를 확인한다.

기대 결과:

- [x] `seeded bids:` 출력이 보인다.
- [x] 최소 3건 이상의 공고가 저장된다.

## 4. 동기화 커맨드 검증

- [x] `python -m app.sync_bid_public_info --begin ... --end ... --operation getBidPblancListInfoServc`
- [x] 성공 시 fetched/upserted 출력 확인
- [ ] 실패 시 예외 메시지와 `sync_job_logs` 적재 여부 확인

예시:

```bash
python -m app.sync_bid_public_info --begin 202603130000 --end 202603132359 --operation getBidPblancListInfoServc
```

기대 결과:

- [x] 성공 시 `fetched bids:` 와 `upserted bids:` 출력이 보인다.
- [x] `/operations` 또는 DB에서 실행 로그를 확인할 수 있다.

## 5. 메인 화면 검증

- [x] 애플리케이션 실행
- [x] `/bids` 접속
- [x] 목록 렌더링 확인
- [x] 마지막 동기화 시각 표시 확인

기대 결과:

- [x] 입찰 목록 테이블이 렌더링된다.
- [x] 첫 행 기준 상세 Drawer가 정상 표시된다.

## 6. 목록 필터 검증

- [x] 키워드 필터: `/bids?q=구급소모품`
- [x] 상태 필터: `/bids?status=collected`
- [ ] 관심 필터: `/bids?favorites=1`
- [x] 조합 필터: `/bids?q=구급소모품&status=collected&favorites=1`

기대 결과:

- [x] 조건에 맞는 행만 남는다.
- [x] 필터 입력값이 화면에 유지된다.
- [x] HTMX 요청 후에도 URL이 동기화된다.

## 7. 상세 Drawer 검증

- [x] 목록 행 클릭
- [x] `/partials/bids/{bid_id}/drawer` 응답 확인
- [x] `/partials/bids/{bid_id}/timeline-inline` 응답 확인

기대 결과:

- [x] 공고일반, 자격/제한, 첨부파일, 타임라인, 이력 섹션이 보인다.
- [x] 상세 본문이 없으면 fallback 문구가 노출된다.
- [x] 첨부파일이 있으면 정렬된 순서로 보인다.

## 8. 관심 공고 화면 검증

- [x] `/favorites` 접속
- [x] 공통 필터 바 노출 확인
- [x] `/favorites?q=신기`
- [x] `/partials/favorites/table?status=favorite`

기대 결과:

- [x] 관심 공고만 노출된다.
- [x] 필터 바가 `/favorites` 경로 기준으로 동작한다.
- [x] 관심 전용 배지가 표시되고 hidden `favorites=1`이 유지된다.

## 9. 운영 화면 검증

- [x] `/operations` 접속
- [ ] 상태 필터: `/operations?status=failed`
- [ ] 작업유형 필터: `/operations?job_type=bid_public_info_sync`

기대 결과:

- [x] 최근 실행 로그가 최신순으로 보인다.
- [x] 성공/실패 메시지가 요약 카드와 목록에 반영된다.
- [x] 실패 로그에서 `operation`, `exception_type`, `retry_count`, `status_code` 같은 정보가 확인된다.

## 10. 기록 항목

- [x] 사용한 `DATABASE_URL`
- [x] 사용한 `BID_DATA_BACKEND`
- [x] 실행한 sync 명령
- [ ] 실패 케이스가 있으면 재현 조건
- [x] 확인한 화면: `/bids`, `/favorites`, `/operations`

## 11. 완료 기준

- [x] 자동 테스트 통과
- [x] seed 후 메인 화면 확인 완료
- [x] sync 후 운영 로그 확인 완료
- [x] 목록/상세/관심/운영 화면 핵심 흐름 확인 완료

## 12. Empty/Error State 확인

- [x] 빈 DB에서 `/bids` 접근 시 `표시할 공고가 없습니다.` 노출
- [x] 빈 DB에서 `/favorites` 접근 시 `표시할 관심 공고가 없습니다.` 노출
- [x] 빈 DB에서 `/operations` 접근 시 `표시할 작업 이력이 없습니다.` 노출
- [x] 상세 Drawer 보조 섹션은 데이터가 없을 때 empty state 또는 안내 문구를 유지

## 13. 2026-03-13 실행 메모

- [x] 검증 DB: `sqlite:///./manual-phase1-sync.db`
- [x] 백엔드 모드: `BID_DATA_BACKEND=sqlmodel`
- [x] 실제 sync 실행: `python -m app.sync_bid_public_info --begin 202603120000 --end 202603132359 --operation getBidPblancListInfoServc --rows 20`
- [x] sync 결과 확인: `fetched 20 bids, upserted 20 bids`
- [x] 저장 결과 확인: `bids=20`, `bid_details=20`
- [x] 운영 로그 확인: `sync_job_logs` 최신 항목 `completed`, target=`getBidPblancListInfoServc`
- [x] 화면 확인: `/bids`, `/partials/bids/R26BK00000001-000/drawer`, `/operations`
- [x] 실제 sync 데이터 기준 `/favorites` 검증

추가 메모:

- [x] 검증을 위해 최신 sync 공고 1건(`R26BK01386273-000`)에 `is_favorite=True`를 수동 부여
- [x] `/favorites`, `/partials/favorites/table`, `/favorites?status=collected`에서 표시 확인
