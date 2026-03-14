# Internal API: Bids

## 1. 주요 도메인 모델

### BidSummary

```json
{
  "bid_id": "20260312001-00",
  "bid_no": "20260312001",
  "bid_seq": "00",
  "title": "Woorisoft AI 자동화 솔루션 도입 사업",
  "demand_org": "조달청",
  "notice_org": "정부전산센터",
  "status": "reviewing",
  "bid_status_label": "검토중",
  "posted_at": "2026-03-12T09:00:00+09:00",
  "closed_at": "2026-03-20T18:00:00+09:00",
  "budget_amount": 500000000,
  "is_favorite": true,
  "last_synced_at": "2026-03-12T09:10:00+09:00"
}
```

### BidDetail

```json
{
  "bid": {},
  "description_text": "공고문 본문 요약 또는 정제 텍스트",
  "raw_api_data": {},
  "crawl_data": {},
  "attachments": [],
  "timeline": []
}
```

### Attachment

```json
{
  "attachment_id": "att_001",
  "name": "제안요청서.pdf",
  "file_type": "pdf",
  "download_url": "https://example.com/file.pdf",
  "local_path": "/data/files/20260312001-00/rfp.pdf",
  "collected_at": "2026-03-12T09:11:00+09:00"
}
```

### TimelineEvent

```json
{
  "stage": "bid_notice",
  "label": "입찰공고",
  "occurred_at": "2026-03-12T09:00:00+09:00",
  "status": "completed",
  "source": "api"
}
```

## 2. API 목록

### 2.1 헬스체크

#### `GET /api/v1/health`

- 목적: 서버와 주요 의존성 상태 확인

### 2.2 공고 리스트 조회

#### `GET /api/v1/bids`

- 목적: 메인 화면 공고 리스트 조회
- 구현 상태: 구현 완료
- Swagger 문서 노출: 포함

쿼리 파라미터:

- `q`: 공고명, 기관명, 공고번호 통합 검색
- `status`: 현재 저장/표시 상태값 필터
- `favorites_only`: 관심 공고만 조회 (`true|false`)
- `keyword`: 설명, 자격요건, 업종/물품 분류 등 상세 키워드 검색
- `page`: 페이지 번호
- `page_size`: 페이지 크기 (1-100)
- `sort`: 정렬 기준 (`posted_at`, `closed_at`, `budget_amount`)
- `order`: 정렬 방향 (`asc`, `desc`)

현재 구현 응답 형식:

```json
{
  "success": true,
  "data": {
    "items": []
  },
  "meta": {
    "total": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "search_query": "구급소모품",
    "keyword": "데이터서비스",
    "status": "수집완료",
    "favorites_only": false,
    "sort": "posted_at",
    "order": "desc"
  },
  "error": null
}
```

현재 미구현 파라미터:


### 2.3 공고 상세 조회

#### `GET /api/v1/bids/{bid_id}`

- 목적: 상세 Drawer 또는 상세 페이지 데이터 조회
- 구현 상태: 구현 완료
- Swagger 문서 노출: 포함

현재 구현 응답 형식:

```json
{
  "success": true,
  "data": {},
  "meta": {},
  "error": null
}
```

없는 공고 조회 시:

```json
{
  "success": false,
  "data": null,
  "meta": {},
  "error": {
    "code": "BID_NOT_FOUND",
    "message": "해당 공고를 찾을 수 없습니다."
  }
}
```

### 2.4 공고 상태 변경

#### `PATCH /api/v1/bids/{bid_id}/status`

- 목적: 내부 관리 상태 변경
- 구현 상태: 구현 완료
- Swagger 문서 노출: 포함

요청 형식:

```json
{
  "status": "reviewing"
}
```

응답 형식:

```json
{
  "success": true,
  "data": {},
  "meta": {},
  "error": null
}
```

허용 상태값:

- `collected`
- `reviewing`
- `favorite`
- `submitted`
- `won`
- `archived`

### 2.5 관심 공고 등록/해제

#### `POST /api/v1/bids/{bid_id}/favorite`

- 목적: 공고를 관심 목록에 등록
- 구현 상태: 구현 완료
- Swagger 문서 노출: 포함

#### `DELETE /api/v1/bids/{bid_id}/favorite`

- 목적: 관심 공고 해제
- 구현 상태: 구현 완료
- Swagger 문서 노출: 포함

### 2.6 수동 재수집 실행

#### `POST /api/v1/bids/{bid_id}/resync`

- 목적: 특정 공고의 API/크롤링 재수집 작업 실행
- 동작: 백그라운드 태스크에서 상세 보강과 Playwright 크롤링을 순차 실행하고 `sync_job_logs`에 상태를 기록
- 구현 상태: 구현 완료
- Swagger 문서 노출: 포함

### 2.7 일괄 동기화 실행

#### `POST /api/v1/sync/daily`

- 목적: 일일 배치 수집 작업 수동 실행
- 권한: 관리자 전용

### 2.8 동기화 작업 상태 조회

#### `GET /api/v1/jobs/{job_id}`

- 목적: 수집/재수집 작업 상태 확인
- 구현 상태: 구현 완료
- Swagger 문서 노출: 포함

### 2.9 첨부파일 목록 조회

#### `GET /api/v1/bids/{bid_id}/attachments`

- 목적: 공고 첨부파일 목록만 별도 조회
- 구현 상태: 구현 완료
- Swagger 문서 노출: 포함

### 2.10 타임라인 조회

#### `GET /api/v1/bids/{bid_id}/timeline`

- 목적: 계약 과정 통합 타임라인 조회
- 구현 상태: 구현 완료
- Swagger 문서 노출: 포함

### 2.11 사전 탐색 리스트 조회

#### `GET /api/v1/prespecs`

- 목적: 발주계획 및 사전규격 리스트 조회

### 2.12 사후 분석 리스트 조회

#### `GET /api/v1/results`

- 목적: 낙찰/계약 결과 및 분석용 데이터 조회

### 2.13 목록 내보내기

#### `GET /api/v1/bids/export`

- 목적: 현재 필터 기준 공고 리스트 다운로드
- 구현 상태: 구현 완료
- Swagger 문서 노출: 포함
- 응답: `text/csv` (`bids-export.csv`, Excel 열기 가능)
