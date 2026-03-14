# g2b

Woorisoft G2B 입찰 자동화 및 관리 대시보드 프로젝트 초기 개발환경 문서.

현재 이 저장소에서는 `pip` 경로와 `uv` 경로 모두 기본 설치, 테스트, 개발 서버 실행까지 검증했다.

## 빠른 시작

### 1. Python 준비

- Python 3.11 이상 설치

### 2. 의존성 설치

기본 권장 경로:

```bash
pip install -e .
```

이 방식으로 프로젝트 패키지와 런타임 의존성이 함께 설치된다.

`uv` 사용 시:

```bash
python -m uv sync
```

둘 중 하나만 선택해서 사용하면 된다.

### 3. 환경 변수 준비

```bash
copy .env.example .env
```

### 4. 개발 서버 실행

기본 경로:

```bash
uvicorn app.main:app --reload
```

`uv` 사용 시:

```bash
python -m uv run uvicorn app.main:app --reload
```

### 5. 테스트 실행

기본 경로:

```bash
pytest
```

`uv` 사용 시:

```bash
python -m uv run pytest
```

### 6. 샘플 데이터를 SQLite에 적재하고 싶을 때

기본값은 `BID_DATA_BACKEND=auto` 이며, DB에 수집/seed 데이터가 있으면 이를 우선 사용하고, 없으면 샘플 메모리 데이터를 표시한다.

SQLite 저장 데이터만 강제로 사용하려면 `.env`에서 `BID_DATA_BACKEND=sqlmodel` 로 변경한 뒤 아래 명령을 실행한다.

```bash
python -m app.seed_bids
```

로그를 줄이고 결과만 확인하려면:

```bash
python -m app.seed_bids --quiet
```

`uv` 사용 시:

```bash
python -m uv run python -m app.seed_bids --quiet
```

### 7. G2B 입찰공고정보서비스 1차 동기화

실제 G2B API로 기본 공고 목록을 수집해 `bids`, `bid_details` 테이블에 저장하려면 `.env`에 서비스 키를 설정한 뒤 아래 명령을 실행한다.

```bash
python -m app.sync_bid_public_info --begin 202603120000 --end 202603132359
```

`uv` 사용 시:

```bash
python -m uv run python -m app.sync_bid_public_info --begin 202603120000 --end 202603132359
```

옵션:

- `--begin`: 조회 시작 시각 (`YYYYMMDDHHMM`)
- `--end`: 조회 종료 시각 (`YYYYMMDDHHMM`)
- `--rows`: 호출당 조회 건수
- `--operation`: 특정 오퍼레이션만 수집할 때 사용, 여러 번 지정 가능

동기화가 끝나면 실행 결과가 `sync_job_logs` 테이블에 저장되고, `BID_DATA_BACKEND=auto` 또는 `sqlmodel` 환경에서는 `/operations` 화면에서 최근 성공/실패 이력을 바로 확인할 수 있다.

### 8. Playwright 상세 페이지 크롤링 준비

Playwright 기반 상세 본문/첨부 메타데이터 수집을 실행하려면 브라우저 런타임을 한 번 설치해야 한다.

```bash
python -m pip install playwright
python -m playwright install chromium
```

특정 공고 상세 페이지를 직접 크롤링하려면:

```bash
python -m app.sync_bid_crawl --bid-id R26BK01387837-000
```

크롤링 결과는 `bid_details.crawl_data`, `attachments(source=playwright_detail)`, `sync_job_logs`에 저장된다.

### 9. Admin Sync API 사용

Swagger UI에서 내부 관리자용 sync API를 테스트할 수 있다.

- 문서 경로: `/docs`
- OpenAPI 원본: `/openapi.json`
- 대상 라우트: `/admin/sync/*`, `/admin/operations`
- 필수 헤더: `X-Admin-Token`
- Swagger UI에는 JSON API만 노출되며, 화면 렌더링용 `/partials/*`, `/bids` 등은 제외된다.

개발 기본값:

```bash
set ADMIN_SYNC_TOKEN=dev-admin-token
```

사용 순서:

1. 서버 실행 후 `http://127.0.0.1:8000/docs` 접속
2. 우측 상단 `Authorize` 클릭
3. `APIKeyHeader` 값에 `dev-admin-token` 입력
4. 원하는 `/admin/sync/*` 엔드포인트를 펼쳐서 Example payload로 실행
5. 실패 시 Swagger UI의 `401`, `403`, `422` 예시 응답을 기준으로 원인 확인

예시 요청:

```bash
curl -X POST "http://127.0.0.1:8000/admin/sync/phase2-batch" ^
  -H "Content-Type: application/json" ^
  -H "X-Admin-Token: dev-admin-token" ^
  -d "{\"selection_mode\":\"targeted\",\"recent_days\":7}"
```

주요 엔드포인트:

- `POST /admin/sync/bid-public-info`
- `POST /admin/sync/bid-detail-enrichment`
- `POST /admin/sync/contract-process`
- `POST /admin/sync/bid-crawl`
- `POST /admin/sync/phase2-batch`
- `GET /admin/operations`

문서에 포함된 예시:

- 각 sync 요청 body 예시
- 성공 응답 예시
- 인증 실패(`401`, `403`) 예시
- 요청 검증 실패(`422`) 예시

### 10. Public Bids JSON API 사용

Swagger UI에서 서비스용 조회 API도 함께 확인할 수 있다.

- 문서 경로: `/docs`
- OpenAPI 원본: `/openapi.json`
- 대상 라우트: `/api/v1/bids`, `/api/v1/bids/{bid_id}`, `/api/v1/health`
- 상태 변경 라우트: `/api/v1/bids/{bid_id}/status`
- 관심 공고 라우트: `/api/v1/bids/{bid_id}/favorite`
- 첨부파일 라우트: `/api/v1/bids/{bid_id}/attachments`
- 타임라인 라우트: `/api/v1/bids/{bid_id}/timeline`
- 재수집 라우트: `/api/v1/bids/{bid_id}/resync`
- 작업 상태 라우트: `/api/v1/jobs/{job_id}`
- 내보내기 라우트: `/api/v1/bids/export`
- 응답 형식: `success`, `data`, `meta`, `error` 공통 wrapper 사용
- 목록 쿼리: `q`, `status`, `favorites_only`, `keyword`, `org`, `budget_min`, `budget_max`, `closed_from`, `closed_to`, `page`, `page_size`, `sort`, `order`

예시 요청:

```bash
curl "http://127.0.0.1:8000/api/v1/bids?q=구급소모품&status=수집완료"
```

```bash
curl "http://127.0.0.1:8000/api/v1/bids?page=2&page_size=1&sort=budget_amount&order=asc"
```

```bash
curl "http://127.0.0.1:8000/api/v1/bids?org=전라남도&budget_min=1000000000&closed_from=2026-03-17%2000:00"
```

```bash
curl "http://127.0.0.1:8000/api/v1/bids?keyword=데이터서비스"
```

```bash
curl -OJ "http://127.0.0.1:8000/api/v1/bids/export?status=검토중&sort=budget_amount&order=desc"
```

```bash
curl "http://127.0.0.1:8000/api/v1/bids/R26BK00000003-000"
```

```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/bids/R26BK00000002-000/status" ^
  -H "Content-Type: application/json" ^
  -d "{\"status\":\"reviewing\"}"
```

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/bids/R26BK00000002-000/favorite"
```

```bash
curl -X DELETE "http://127.0.0.1:8000/api/v1/bids/R26BK00000002-000/favorite"
```

```bash
curl "http://127.0.0.1:8000/api/v1/bids/R26BK00000001-000/attachments"
```

```bash
curl "http://127.0.0.1:8000/api/v1/bids/R26BK00000001-000/timeline"
```

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/bids/R26BK00000001-000/resync"
```

```bash
curl "http://127.0.0.1:8000/api/v1/jobs/101"
```

주요 동작:

- `GET /api/v1/bids`: 검색어, 상태, 관심 공고 여부로 목록 필터링
- `GET /api/v1/bids`: `posted_at`, `closed_at`, `budget_amount` 기준 정렬과 페이지네이션 지원
- `GET /api/v1/bids/{bid_id}`: 단건 상세 조회
- `PATCH /api/v1/bids/{bid_id}/status`: 내부 상태값(`collected`, `reviewing`, `favorite`, `submitted`, `won`, `archived`) 변경
- `POST /api/v1/bids/{bid_id}/favorite`: 관심 공고 등록
- `DELETE /api/v1/bids/{bid_id}/favorite`: 관심 공고 해제
- `GET /api/v1/bids/{bid_id}/attachments`: 첨부파일 목록만 별도 조회
- `GET /api/v1/bids/{bid_id}/timeline`: 타임라인 정보만 별도 조회
- `POST /api/v1/bids/{bid_id}/resync`: 상세 보강 + 상세 페이지 크롤링 재수집 작업 실행
- `GET /api/v1/jobs/{job_id}`: 재수집/동기화 작업 상태 조회
- `GET /api/v1/bids/export`: 현재 필터 기준 CSV 다운로드(Excel 열기 가능)
- 결과 없음 또는 없는 공고 조회 시 `404`와 공통 에러 wrapper 반환

## 문서 구조

- 제품 정의
  - `docs/PRD.md`
- API
  - `docs/api/api-spec.md`
  - `docs/api/overview.md`
  - `docs/api/internal-bids.md`
  - `docs/api/external-g2b-bid-public-info.md`
  - `docs/api/external-g2b-industry.md`
  - `docs/api/external-g2b-contract-process.md`
  - `docs/api/api-sync-strategy.md`
- 아키텍처
  - `docs/architecture/system-architecture.md`
  - `docs/architecture/code-architecture.md`
- 데이터
  - `docs/data/data-model.md`
  - `docs/data/er-relationship.md`
  - `docs/data/parsing/contract-process-subdatasets.md`
- 프론트엔드
  - `docs/frontend/frontend-architecture.md`
  - `docs/frontend/frontend-design-guide.md`
  - `docs/frontend/frontend-wireframes.md`
  - `docs/frontend/frontend-template-structure.md`
  - `docs/frontend/frontend-ui-tokens.md`
  - `docs/frontend/frontend-column-priority.md`
  - `docs/frontend/frontend-stage-card-spec.md`
  - `docs/frontend/frontend-main-html-blocks.md`
  - `docs/frontend/frontend-view-models.md`
  - `docs/frontend/frontend-implementation-checklist.md`
- 참고 자료
  - `docs/reference/g2b/`
  - `docs/README.md`

## 현재 코드 구조

```text
app/
  config.py
  db.py
  main.py
  models/
  sample_data/
  repositories/
  services/
  presentation/
    mappers/
    viewmodels/
templates/
tests/
```

레이어 역할:

- `sample_data/`: 샘플 원본 데이터
- `repositories/`: 데이터 접근 추상화 및 구현체
- `services/`: 화면/도메인 조회 서비스
- `presentation/mappers/`: 원본/정규화 데이터 -> 화면용 view-model 변환
- `presentation/viewmodels/`: 템플릿 전용 데이터 구조
- `templates/`: Jinja2 + HTMX 렌더링 계층
- `main.py`: 라우팅과 페이지 컨텍스트 조립

## 환경 변수

### 공통 앱 설정

- `APP_NAME`: 애플리케이션 이름
- `APP_ENV`: 실행 환경 (`development`, `production` 등)
- `DEBUG`: 디버그 모드 여부
- `DATABASE_URL`: DB 연결 문자열
- `BID_DATA_BACKEND`: 입찰 데이터 소스 (`auto`, `sample`, `sqlmodel`)

### G2B API 설정

- `G2B_API_SERVICE_KEY_ENCODED`: 공공데이터포털 인코딩 인증키
- `G2B_API_SERVICE_KEY_DECODED`: 공공데이터포털 디코딩 인증키
- `G2B_API_BID_PUBLIC_INFO_BASE_URL`: 입찰공고정보서비스 Base URL
- `G2B_API_INDUSTRY_BASE_URL`: 업종 및 근거법규서비스 Base URL
- `G2B_API_CONTRACT_PROCESS_BASE_URL`: 계약과정통합공개서비스 Base URL

설정 객체 매핑:

- `app/config.py`의 `Settings`가 위 환경변수를 읽는다.
- 주요 키:
  - `g2b_api_bid_public_info_base_url`
  - `g2b_api_industry_base_url`
  - `g2b_api_contract_process_base_url`

## 다음 구현 대상

- 설정 로더 고도화
- SQLModel 엔티티 추가
- SQLite 초기화 및 마이그레이션 도입
- 외부 OpenAPI 수집기 추가
