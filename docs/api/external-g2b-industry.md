# External API: G2B Industry Base Law Rules

## 1. 개요

- 목적: 나라장터 업종 코드, 분류명, 근거법령, 관련 규정 정보를 수집해 내부 기준 데이터로 활용한다.
- 서비스 ID: `IndstrytyBaseLawrgltInfoService`
- 오퍼레이션명: `getIndstrytyBaseLawrgltInfoList02`
- 방식: `REST(GET)`
- 응답 포맷: `XML`, `JSON`
- 데이터 갱신주기: 수시
- 평균 응답시간: 약 `500ms`
- 최대 트랜잭션: `30 tps`

## 2. 엔드포인트

```text
https://apis.data.go.kr/1230000/ao/IndstrytyBaseLawrgltInfoService/getIndstrytyBaseLawrgltInfoList02
```

참고:

- 포털 화면이나 일부 안내에서는 `/getIndstrytyBaseLawrgltInfoList`처럼 보일 수 있으나, 실제 오퍼레이션 경로는 `getIndstrytyBaseLawrgltInfoList02` 기준으로 관리한다.

## 3. 요청 파라미터

| 파라미터 | 필수 | 설명 |
|---|---|---|
| `serviceKey` | Y | 공공데이터포털 인증키 |
| `pageNo` | Y | 페이지 번호 |
| `numOfRows` | Y | 한 페이지 결과 수 |
| `type` | N | `json` 지정 시 JSON 응답 |
| `indstrytyClsfcCd` | N | 업종분류코드 |
| `indstrytyNm` | N | 업종명 |
| `indstrytyCd` | N | 업종코드 |
| `inqryBgnDt` | N | 조회시작일시, 형식 `YYYYMMDDHHMM` |
| `inqryEndDt` | N | 조회종료일시, 형식 `YYYYMMDDHHMM` |
| `indstrytyUseYn` | N | 업종사용여부, 예: `Y` |

## 4. 요청 예시

```http
GET https://apis.data.go.kr/1230000/ao/IndstrytyBaseLawrgltInfoService/getIndstrytyBaseLawrgltInfoList02?serviceKey={ENCODED_SERVICE_KEY}&pageNo=1&numOfRows=10&type=json&indstrytyClsfcCd=41&indstrytyNm=%EB%82%98%EB%AC%B4%EB%B3%91%EC%9B%90%281%EC%A2%85%29&indstrytyCd=4161&indstrytyUseYn=Y
```

```bash
curl "https://apis.data.go.kr/1230000/ao/IndstrytyBaseLawrgltInfoService/getIndstrytyBaseLawrgltInfoList02?serviceKey=${G2B_API_SERVICE_KEY_ENCODED}&pageNo=1&numOfRows=10&type=json&indstrytyClsfcCd=41&indstrytyNm=%EB%82%98%EB%AC%B4%EB%B3%91%EC%9B%90%281%EC%A2%85%29&indstrytyCd=4161&indstrytyUseYn=Y"
```

## 5. 응답 핵심 필드

| 필드 | 설명 |
|---|---|
| `resultCode` | 결과코드 |
| `resultMsg` | 결과메시지 |
| `numOfRows` | 한 페이지 결과 수 |
| `pageNo` | 페이지 번호 |
| `totalCount` | 전체 결과 수 |
| `indstrytyClsfcCd` | 업종분류코드 |
| `indstrytyClsfcNm` | 업종분류명 |
| `indstrytyCd` | 업종코드 |
| `indstrytyNm` | 업종명 |
| `baseLawordNm` | 근거법령명 |
| `baseLawordArtclClauseNm` | 근거법령조항명 |
| `baseLawordUrl` | 근거법령 URL |
| `rltnRgltCntnts` | 관련 규정 내용 |
| `inclsnLcns` | 포함면허 서브데이터셋 문자열 |
| `indstrytyUseYn` | 업종사용여부 |
| `indstrytyRgstDt` | 업종등록일시 |
| `indstrytyChgDt` | 업종변경일시 |

## 6. 응답 예시

```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "정상"
    },
    "body": {
      "items": [
        {
          "indstrytyClsfcCd": "41",
          "indstrytyClsfcNm": "산림",
          "indstrytyCd": "4161",
          "indstrytyNm": "나무병원(1종)",
          "baseLawordNm": "산림보호법",
          "baseLawordArtclClauseNm": "제21조의9",
          "baseLawordUrl": "",
          "rltnRgltCntnts": "",
          "inclsnLcns": "",
          "indstrytyUseYn": "Y",
          "indstrytyRgstDt": "2018-06-29 17:22:43",
          "indstrytyChgDt": "2024-05-02 11:00:48"
        }
      ],
      "numOfRows": 10,
      "pageNo": 1,
      "totalCount": 1
    }
  }
}
```

## 7. 수집 및 정규화 메모

- `indstrytyCd`는 내부 기준 업종 코드 마스터의 핵심 식별자로 사용 가능하다.
- `indstrytyClsfcCd`, `indstrytyClsfcNm`는 상위 분류 체계로 별도 컬럼 저장을 권장한다.
- `baseLawordNm`, `baseLawordArtclClauseNm`, `baseLawordUrl`, `rltnRgltCntnts`는 법령 근거 설명용 메타데이터로 저장한다.
- `indstrytyUseYn='Y'` 기준만 기본 동기화 대상으로 삼고, 비활성 코드까지 필요한 경우 전체 적재 후 상태 컬럼으로 관리한다.
- `inclsnLcns`는 `[순번^제한업종코드^제한업종명^허용업종코드^허용업종명]` 형태의 반복 데이터이므로, 파싱 후 별도 관계 테이블로 분리하는 것이 좋다.

## 8. 에러 코드 운영 메모

| 코드 | 의미 | 대응 |
|---|---|---|
| `00` | 정상 | 정상 처리 |
| `03` | 데이터 없음 | 빈 결과로 처리 |
| `06` | 날짜 포맷 오류 | 요청 날짜 포맷 검증 |
| `07` | 입력범위값 초과 | 페이지/행수/입력 범위 재검토 |
| `08` | 필수값 입력 에러 | 필수 파라미터 누락 확인 |
| `10` | 잘못된 요청 파라미터 | `serviceKey` 및 URL 확인 |
| `20` | 서비스 접근 거부 | 활용신청 승인 상태 확인 |
| `22` | 요청 횟수 초과 | 일일 트래픽 관리 및 호출량 제한 |
| `30` | 등록되지 않은 서비스 키 | 인증키 재확인 및 URL 인코딩 확인 |
| `31` | 기한 만료된 서비스 키 | 활용기간 연장 필요 |
| `32` | 등록되지 않은 도메인/IP | 등록 서버 정보 확인 |

## 9. 구현 권장 사항

- 외부 API 호출 시 `type=json`을 기본값으로 사용한다.
- 날짜 파라미터는 애플리케이션 단에서 `YYYYMMDDHHMM` 형식으로 강제한다.
- 응답 `resultCode`가 `00`이 아니면 HTTP 200이어도 실패로 간주하고 별도 에러 처리한다.
- 일일 트래픽 `1000` 제한을 고려해 기준정보 동기화는 배치 캐시 전략으로 운영한다.
- 운영 키는 환경 변수로 관리하고 문서나 코드에 직접 기록하지 않는다.
