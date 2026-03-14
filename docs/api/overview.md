# API Overview

## 1. 개요

- 본 문서는 `docs/PRD.md` 기준 MVP 및 초기 운영 범위의 API 공통 규칙을 정의한다.
- API 스타일은 REST 기반 JSON 응답을 기본으로 한다.
- 서버 프레임워크는 FastAPI를 기준으로 설계한다.
- 화면 렌더링이 Jinja2 + HTMX 기반이더라도, 데이터 조회와 수집 제어는 API 중심으로 분리한다.

## 2. 공통 규칙

### Base Path

```text
/api/v1
```

### Content Type

```http
Content-Type: application/json
```

### 공통 응답 형식

```json
{
  "success": true,
  "data": {},
  "meta": {},
  "error": null
}
```

### 공통 에러 형식

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

### 공통 상태 코드

- `200 OK`: 정상 조회 또는 수정 성공
- `201 Created`: 신규 생성 성공
- `202 Accepted`: 비동기 작업 접수 성공
- `400 Bad Request`: 잘못된 요청 파라미터
- `401 Unauthorized`: 인증 필요
- `403 Forbidden`: 권한 없음
- `404 Not Found`: 리소스 없음
- `409 Conflict`: 중복 또는 상태 충돌
- `500 Internal Server Error`: 서버 오류

## 3. 인증 및 권한

- 사내 전용 시스템을 전제로 하며, 외부 접근은 Cloudflare Zero Trust 뒤에서 제한한다.
- 초기 MVP는 네트워크 레벨 접근 제어를 우선 적용하고, 애플리케이션 레벨 사용자 인증은 후속 단계로 확장 가능하도록 설계한다.
- 사용자별 관심 공고, 메모 기능을 사용할 경우 세션 또는 SSO 연동용 사용자 식별자(`user_id`)가 필요하다.

## 4. HTMX 파셜 원칙

- HTML 파셜 응답은 API와 별도 네임스페이스로 분리하는 것을 권장한다.
- 예시:
  - `GET /partials/bids/table`
  - `GET /partials/bids/{bid_id}/drawer`
  - `GET /partials/dashboard/summary`

권장 원칙:

- JSON API는 데이터 계약 중심으로 유지한다.
- HTMX 파셜은 서버 렌더링된 HTML 조각 반환에 집중한다.
- 동일 비즈니스 로직을 API 서비스 계층에서 재사용한다.

## 5. 유효성 검증 규칙

- `bid_id`는 `공고번호-차수` 형식을 따른다.
- `page`는 1 이상이어야 한다.
- `page_size`는 1 이상 100 이하로 제한한다.
- `budget_min`은 0 이상이어야 한다.
- `budget_max`는 `budget_min` 이상이어야 한다.
- `closed_from`은 `closed_to`보다 늦을 수 없다.
- 상태값은 사전 정의된 enum만 허용한다.

## 6. 로깅 및 감사 포인트

- 수동 재수집 요청 시 요청자, 요청 시각, 대상 공고, 실행 결과를 기록한다.
- 상태 변경 시 이전 상태와 변경 후 상태를 감사 로그에 남긴다.
- 일괄 동기화 실행 시 작업 ID, 수집 건수, 실패 건수, 평균 처리 시간을 기록한다.

## 7. 향후 확장 항목

- 사용자 인증/권한 API
- 경쟁사 분석 API
- 메모/코멘트 API
- 알림 API (마감 임박, 상태 변경, 신규 키워드 매칭)
- 통계 대시보드 API

## 8. 구현 우선순위

### MVP 우선 구현

- `GET /api/v1/health`
- `GET /api/v1/bids`
- `GET /api/v1/bids/{bid_id}`
- `PATCH /api/v1/bids/{bid_id}/status`
- `POST /api/v1/bids/{bid_id}/favorite`
- `DELETE /api/v1/bids/{bid_id}/favorite`
- `POST /api/v1/bids/{bid_id}/resync`
- `GET /api/v1/bids/export`

### 2차 구현

- `POST /api/v1/sync/daily`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/prespecs`
- `GET /api/v1/results`
- HTMX 파셜 엔드포인트
