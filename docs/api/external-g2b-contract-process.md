# External API: G2B Contract Process Integrated Open

## 1. 개요

- 목적: 입찰공고번호, 사전규격등록번호, 발주계획번호, 조달요청번호 중 하나를 기준으로 사전규격 -> 입찰공고 -> 낙찰 -> 계약의 진행과정을 통합 조회한다.
- 서비스 ID: `CntrctProcssIntgOpenService`
- 서비스명: 나라장터 계약과정통합공개서비스
- 방식: `REST(GET)`
- 응답 포맷: `XML`, `JSON`
- 데이터 갱신주기: 수시
- 평균 응답시간: 약 `500ms`
- 최대 트랜잭션: `30 tps`

## 2. 엔드포인트

기본 엔드포인트:

```text
https://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService
```

오퍼레이션 목록:

- `getCntrctProcssIntgOpenFrgcpt`: 외자 조회
- `getCntrctProcssIntgOpenThng`: 물품 조회
- `getCntrctProcssIntgOpenServc`: 용역 조회
- `getCntrctProcssIntgOpenCnstwk`: 공사 조회

### 상세기능 요약

| NO | 오퍼레이션명 | 경로 | 업무구분 | 설명 | 일일 트래픽 |
|---|---|---|---|---|---|
| 1 | `getCntrctProcssIntgOpenFrgcpt` | `/getCntrctProcssIntgOpenFrgcpt` | 외자 | 입찰공고번호, 사전규격등록번호, 발주계획번호, 조달요청번호 중 하나로 외자 입찰공고의 진행과정 조회 | `1000` |
| 2 | `getCntrctProcssIntgOpenThng` | `/getCntrctProcssIntgOpenThng` | 물품 | 입찰공고번호, 사전규격등록번호, 발주계획번호, 조달요청번호 중 하나로 물품 입찰공고의 진행과정 조회 | `1000` |
| 3 | `getCntrctProcssIntgOpenServc` | `/getCntrctProcssIntgOpenServc` | 용역 | 입찰공고번호, 사전규격등록번호, 발주계획번호, 조달요청번호 중 하나로 용역 입찰공고의 진행과정 조회 | `1000` |
| 4 | `getCntrctProcssIntgOpenCnstwk` | `/getCntrctProcssIntgOpenCnstwk` | 공사 | 입찰공고번호, 사전규격등록번호, 발주계획번호, 조달요청번호 중 하나로 공사 입찰공고의 진행과정 조회 | `1000` |

공통 메모:

- `입찰공고번호` 조회 시 `입찰공고차수`는 선택 입력이다.
- 네 기능 모두 조회 키와 응답 구조는 유사하고, 업무구분만 다르다.
- 따라서 내부 설계에서는 서비스별로 분리 구현하기보다 `business_type` 기준 통합 클라이언트로 관리하는 것이 적절하다.

설계 메모:

- 네 오퍼레이션의 요청/응답 구조는 거의 동일하고 업무구분만 다르다.
- 내부 설계에서는 `business_type` 추상화(`foreign`, `goods`, `service`, `construction`)로 통합 관리하는 것이 적절하다.

## 3. 공통 요청 파라미터

| 파라미터 | 필수 | 설명 |
|---|---|---|
| `serviceKey` 또는 `ServiceKey` | Y | 공공데이터포털 인증키 |
| `pageNo` | Y | 페이지 번호 |
| `numOfRows` | Y | 한 페이지 결과 수 |
| `type` | N | `json` 지정 시 JSON 응답 |
| `inqryDiv` | Y | 조회구분: `1` 입찰공고번호, `2` 사전규격등록번호, `3` 발주계획번호, `4` 조달요청번호 |
| `bidNtceNo` | 조건부 | 조회구분 `1`인 경우 필수 |
| `bidNtceOrd` | N | 입찰공고차수, 조회구분 `1`일 때 선택 |
| `bfSpecRgstNo` | 조건부 | 조회구분 `2`인 경우 필수 |
| `orderPlanNo` | 조건부 | 조회구분 `3`인 경우 필수 |
| `prcrmntReqNo` | 조건부 | 조회구분 `4`인 경우 필수 |

조회구분 규칙:

- `inqryDiv=1`: `bidNtceNo` 필수, `bidNtceOrd` 선택
- `inqryDiv=2`: `bfSpecRgstNo` 필수
- `inqryDiv=3`: `orderPlanNo` 필수
- `inqryDiv=4`: `prcrmntReqNo` 필수

### `inqryDiv`별 조회 전략

| `inqryDiv` | 기준 키 | 필수 파라미터 | 권장 사용 시점 | 설계 메모 |
|---|---|---|---|---|
| `1` | 입찰공고번호 | `bidNtceNo` | 내부에 공고번호가 이미 있는 경우 가장 우선 | `bidNtceOrd` 없이도 조회 가능하므로 기본 조회 전략으로 적합 |
| `2` | 사전규격등록번호 | `bfSpecRgstNo` | 사전규격 단계만 먼저 확보된 경우 | 본공고 전 단계 연결 확인에 유용 |
| `3` | 발주계획번호 | `orderPlanNo` | 발주계획 기반 선제 추적이 필요한 경우 | 긴 키 형식이므로 저장 시 정규화와 원문 보존을 함께 고려 |
| `4` | 조달요청번호 | `prcrmntReqNo` | 조달요청번호를 별도로 수집/보유한 경우 | 일부 데이터 연결 보조키로 유용하지만 기본 키로는 후순위 |

권장 우선순위:

1. `inqryDiv=1` (`bidNtceNo`)
2. `inqryDiv=2` (`bfSpecRgstNo`)
3. `inqryDiv=3` (`orderPlanNo`)
4. `inqryDiv=4` (`prcrmntReqNo`)

이유:

- 대시보드의 핵심 엔터티가 입찰공고 중심이므로 `bidNtceNo`가 가장 직접적인 연결 키다.
- 사전규격 기반 추적은 본공고 이전 단계 연결에 유리하다.
- 발주계획번호와 조달요청번호는 보조 연결 키로 유용하지만, 실무 UI의 주 조회 흐름은 보통 입찰공고번호 중심이다.

## 4. 오퍼레이션별 요청 예시

### 4.1 외자 조회

```http
GET https://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService/getCntrctProcssIntgOpenFrgcpt?serviceKey={ENCODED_SERVICE_KEY}&pageNo=1&numOfRows=10&type=json&inqryDiv=1&bidNtceNo=20160312130
```

### 4.2 물품 조회

```http
GET https://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService/getCntrctProcssIntgOpenThng?serviceKey={ENCODED_SERVICE_KEY}&pageNo=1&numOfRows=10&type=json&inqryDiv=1&bidNtceNo=20160234982
```

### 4.3 용역 조회

```http
GET https://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService/getCntrctProcssIntgOpenServc?serviceKey={ENCODED_SERVICE_KEY}&pageNo=1&numOfRows=10&type=json&inqryDiv=1&bidNtceNo=20160318205
```

### 4.4 공사 조회

```http
GET https://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService/getCntrctProcssIntgOpenCnstwk?serviceKey={ENCODED_SERVICE_KEY}&pageNo=1&numOfRows=10&type=json&inqryDiv=1&bidNtceNo=20160618729
```

## 5. 공통 응답 핵심 필드

| 필드 | 설명 |
|---|---|
| `resultCode` | 결과코드 |
| `resultMsg` | 결과메시지 |
| `numOfRows` | 한 페이지 결과 수 |
| `pageNo` | 페이지 번호 |
| `totalCount` | 전체 결과 수 |
| `orderPlanNo` | 발주계획번호 |
| `orderPlanUntyNo` | 발주계획통합번호 |
| `orderBizNm` | 발주사업명 |
| `orderInsttNm` | 발주기관명 |
| `orderYm` | 발주년월 |
| `prcrmntMethdNm` | 조달방식명 |
| `cntrctCnclsMthdNm` | 계약체결방법명 |
| `bfSpecRgstNo` | 사전규격등록번호 |
| `bfSpecBizNm` | 사전규격사업명 |
| `bfSpecDminsttNm` | 사전규격수요기관명 |
| `bfSpecNtceInsttNm` | 사전규격공고기관명 |
| `opninRgstClseDt` | 의견등록마감일시 |
| `bidNtceNo` | 입찰공고번호 |
| `bidNtceOrd` | 입찰공고차수 |
| `prcrmntReqNo` | 조달요청번호 |
| `bidNtceNm` | 입찰공고명 |
| `bidDminsttNm` | 입찰수요기관명 |
| `bidMthdNm` | 입찰방법명 |
| `bidNtceDt` | 입찰공고일시 |
| `bidwinrInfoList` | 낙찰자정보목록 문자열 |
| `cntrctInfoList` | 계약정보목록 문자열 |

## 6. 응답 구조 해석 포인트

### `bidwinrInfoList`

- 서브데이터셋 문자열이다.
- 형식:

```text
[순번^낙찰업체명^낙찰업체사업자번호^대표자명^낙찰금액^낙찰률^참가업체수^개찰일시]
```

예시:

```text
[1^한신정보주식회사^6098141001^정상진^108878780^88.041^38^2016-03-07 12:00]
```

### `cntrctInfoList`

- 서브데이터셋 문자열이다.
- 형식:

```text
[순번^계약번호^계약명^계약기관명^계약수요기관명^계약체결방법명^계약금액^계약일자]
```

예시:

```text
[1^2016031744700^인터넷운영 가상화시스템 구입^경상남도 창원시^경상남도 창원시^제한경쟁^108878780^2016-03-09]
```

설계 메모:

- `bidwinrInfoList`, `cntrctInfoList`는 원문 보존 + 별도 정규화 테이블 분리를 함께 고려한다.
- 일부 응답에서는 빈 문자열 또는 self-closing tag로 내려오므로 null/empty 처리 기준이 필요하다.

## 7. 대표 응답 예시

### 7.1 물품 조회 응답 예시

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
          "orderPlanNo": "1-1-2016-5670000-000026-00",
          "orderBizNm": "인터넷 운영 가상화시스템 구입",
          "orderInsttNm": "경상남도 창원시",
          "orderYm": "2016-02",
          "prcrmntMethdNm": "자체조달",
          "cntrctCnclsMthdNm": "제한총액",
          "bfSpecRgstNo": "333556",
          "bfSpecBizNm": "인터넷운영 노후서버 가상화시스템 구축용 H/W, S/W 구매",
          "bfSpecDminsttNm": "경상남도 창원시",
          "bfSpecNtceInsttNm": "경상남도 창원시",
          "opninRgstClseDt": "2016-02-20 23:59",
          "bidNtceNo": "20160234982",
          "bidNtceOrd": "00",
          "prcrmntReqNo": "",
          "bidNtceNm": "인터넷운영 가상화시스템 구입",
          "bidDminsttNm": "경상남도 창원시",
          "bidMthdNm": "전자입찰",
          "bidNtceDt": "2016-02-26 13:28",
          "bidwinrInfoList": "[1^한신정보주식회사^6098141001^정상진^108878780^88.041^38^2016-03-07 12:00]",
          "cntrctInfoList": "[1^2016031744700^인터넷운영 가상화시스템 구입^경상남도 창원시^경상남도 창원시^제한경쟁^108878780^2016-03-09]",
          "orderPlanUntyNo": "1-1-2016-5670000-000026"
        }
      ],
      "numOfRows": 1,
      "pageNo": 1,
      "totalCount": 10
    }
  }
}
```

### 7.2 공사 조회 응답 예시

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
          "orderPlanNo": "3-1-2016-8031000-000038-00",
          "orderBizNm": "홍광초외1교(남당초) 교사 도장공사 소액수의 견적공고",
          "orderInsttNm": "충청북도교육청 충청북도제천교육지원청",
          "orderYm": "2016-06",
          "prcrmntMethdNm": "자체조달",
          "cntrctCnclsMthdNm": "수의",
          "bfSpecRgstNo": "368604",
          "bfSpecBizNm": "홍광초외1교(남당초) 교사도장",
          "bfSpecDminsttNm": "충청북도교육청 충청북도제천교육지원청",
          "bfSpecNtceInsttNm": "충청북도교육청 충청북도제천교육지원청",
          "opninRgstClseDt": "2016-06-21 23:59",
          "bidNtceNo": "20160618729",
          "bidNtceOrd": "00",
          "prcrmntReqNo": "",
          "bidNtceNm": "홍광초외1교(남당초) 교사 도장공사 소액수의 견적공고",
          "bidDminsttNm": "충청북도교육청 충청북도제천교육지원청",
          "bidMthdNm": "전자입찰",
          "bidNtceDt": "2016-06-16 15:34",
          "bidwinrInfoList": "[1^(주)칠공사^3048104950^이대일^48813940^87.769^20^2016-06-22 11:00]",
          "cntrctInfoList": "",
          "orderPlanUntyNo": "3-1-2016-8031000-000038"
        }
      ],
      "numOfRows": 1,
      "pageNo": 1,
      "totalCount": 10
    }
  }
}
```

## 8. 설계상 중요 판단 포인트

- 이 API는 사용자에게 보여줄 타임라인 데이터의 핵심 소스다.
- `inqryDiv`에 따라 조회 키가 달라지므로 내부에서는 단일 함수보다 `query_type + query_value` 구조로 추상화하는 것이 좋다.
- `bidNtceNo`만으로도 조회 가능하고 `bidNtceOrd`는 선택값이므로, 공고 차수 미존재 상태를 기본 시나리오로 지원해야 한다.
- 한 응답 안에 사전규격, 입찰, 낙찰, 계약이 모두 섞여 있으므로 내부 정규화 단계에서 단계별 엔터티로 분해하는 것이 바람직하다.
- `totalCount`가 10으로 내려와도 실제 `items`는 1건일 수 있으므로, 페이지네이션 의미를 실제 호출로 재검증해야 한다.

## 9. G2B 대시보드 설계 활용 포인트

- PRD의 통합 타임라인은 이 API를 중심 데이터 소스로 설계할 수 있다.
- `orderPlanNo`, `bfSpecRgstNo`, `bidNtceNo`, `prcrmntReqNo`를 연결 키 후보로 관리해야 한다.
- 낙찰 정보와 계약 정보는 내부에서 별도 리스트로 분해한 후 상세 Drawer와 분석 화면에서 재사용하는 것이 좋다.
- 비어 있는 `bidwinrInfoList`, `cntrctInfoList`는 진행 중 상태를 의미할 수 있으므로 단순 오류가 아니라 상태 미도달로 해석해야 한다.

## 10. 에러 코드 운영 메모

| 코드 | 의미 | 대응 |
|---|---|---|
| `00` | 정상 | 정상 처리 |
| `03` | 데이터 없음 | 빈 결과로 처리 |
| `06` | 날짜 포맷 오류 | 요청값 검증 |
| `07` | 입력범위값 초과 | 페이지/행수/입력값 범위 확인 |
| `08` | 필수값 입력 에러 | 필수 파라미터 누락 확인 |
| `10` | 잘못된 요청 파라미터 | `serviceKey` 및 URL 확인 |
| `20` | 서비스 접근 거부 | 활용신청 승인 상태 확인 |
| `22` | 요청 횟수 초과 | 호출량 제한 및 배치 관리 |
| `30` | 등록되지 않은 서비스 키 | 인증키 및 인코딩 확인 |
| `31` | 기한 만료된 서비스 키 | 연장 신청 필요 |
| `32` | 등록되지 않은 도메인/IP | 등록 서버 정보 확인 |

## 11. 구현 권장 사항

- 초기 설계 단계에서는 네 오퍼레이션을 개별 문서화하되, 구현 시에는 공통 클라이언트 + 업무구분 enum으로 통합하는 것이 좋다.
- 응답 시간 문자열은 포맷이 완전히 일관적이지 않을 수 있으므로 파서에서 다중 포맷을 허용해야 한다.
- `bidwinrInfoList`, `cntrctInfoList` 파싱 실패 시 원문을 반드시 보존해야 한다.
- 내부 타임라인 저장 시 `raw_api_data`와 단계별 정규화 결과를 함께 유지하는 구조가 적절하다.
