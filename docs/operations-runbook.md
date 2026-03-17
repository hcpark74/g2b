# Operations Runbook

초기 운영 환경에서 배치 실행, 상태 확인, 실패 대응을 위한 최소 절차를 정리한다.

## 1. 확인 경로

- 운영 화면: `/operations`
- 헬스 체크: `/api/v1/health`
- 관리자 수동 실행: `/admin/sync/*`

## 2. 기본 점검 순서

- `/api/v1/health`에서 `status`, `database`, `recent_failed_jobs`, `latest_job`를 확인한다.
- `/operations`에서 최근 실패 job의 `job_type`, `target`, `message`를 확인한다.
- 최근 실패가 `bid_page_crawl`이면 selector/DOM 변경 여부를 먼저 점검한다.
- 최근 실패가 API sync 계열이면 응답 코드, 인증키, 요청 기간, 재시도 횟수를 확인한다.

## 3. 수동 재실행 기준

- 단건 공고 보강 실패: 상세 Drawer의 수동 액션 또는 관련 admin sync를 사용한다.
- 대량 수집 실패: `/admin/sync/bid-public-info`, `/admin/sync/phase2-batch`로 범위를 줄여 재실행한다.
- 크롤링 실패: 대상 `bid_id`만 지정해 `bid_page_crawl`을 다시 실행한다.

## 4. 실패 알림

- `OPS_SLACK_WEBHOOK_URL`가 설정되어 있으면 failed job 기록 시 Slack webhook 알림을 전송한다.
- 알림 본문에는 `job_type`, `target`, `started_at`, `message`를 포함한다.

## 5. 필수 환경변수

- `DATABASE_URL`
- `ADMIN_SYNC_TOKEN`
- `G2B_API_SERVICE_KEY_ENCODED` 또는 `G2B_API_SERVICE_KEY_DECODED`
- `OPS_SLACK_WEBHOOK_URL` (선택, 실패 알림용)

## 6. 초기 운영 판정 기준

- `/api/v1/health`가 `ok` 또는 `degraded`로 응답한다.
- 최근 실패 원인을 `/operations` 또는 Slack 알림에서 판독할 수 있다.
- 실패한 배치를 수동 재실행 절차로 복구할 수 있다.
