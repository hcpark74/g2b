# Parsing Rules: Contract Process Subdatasets

## 1. 개요

- 본 문서는 `CntrctProcssIntgOpenService`의 서브데이터셋 문자열 파싱 규칙을 정의한다.
- 대상 필드:
  - `bidwinrInfoList`
  - `cntrctInfoList`
- 목적은 원문 손실 없이 정규화 가능한 최소 규칙을 고정하는 것이다.

## 2. 공통 원칙

- 원본 문자열은 항상 별도 컬럼에 그대로 저장한다.
- 파싱 성공 여부와 관계없이 원본 적재를 우선한다.
- 파싱 결과가 비어 있어도 오류로 간주하지 않는다.
- 빈 문자열, `null`, self-closing tag는 모두 "데이터 없음"으로 처리한다.
- 파싱 실패 시 전체 수집 실패로 만들지 않고, 파싱 오류 로그와 원문 보존으로 대응한다.

## 3. 원문 형식

서브데이터셋은 대체로 다음 구조를 따른다.

```text
[item1],[item2],...
```

각 item 내부는 `^` 구분자를 사용한다.

```text
[field1^field2^field3]
```

주의:

- PDF 문서의 설명과 실제 응답 사이에 공백, 줄바꿈, 빈값 표현 차이가 있을 수 있다.
- 일부 응답은 항목 하나만 있어도 `[ ... ]` 형태를 유지한다.
- 필드 내부에 쉼표가 포함될 가능성이 낮지만, 우선 파서는 `],[` 경계를 기준으로 item 분리하는 방식이 안전하다.

## 4. `bidwinrInfoList` 파싱 규칙

### 원문 형식

```text
[순번^낙찰업체명^낙찰업체사업자번호^대표자명^낙찰금액^낙찰률^참가업체수^개찰일시]
```

### 필드 매핑

| 순서 | 필드명 | 설명 | 저장 컬럼 |
|---|---|---|---|
| 1 | `seq_no` | 순번 | `seq_no` |
| 2 | `winner_company_name` | 낙찰업체명 | `winner_company_name` |
| 3 | `winner_business_no` | 사업자번호 | `winner_business_no` |
| 4 | `representative_name` | 대표자명 | `representative_name` |
| 5 | `award_amount` | 낙찰금액 | `award_amount` |
| 6 | `award_rate` | 낙찰률 | `award_rate` |
| 7 | `bidder_count` | 참가업체수 | `bidder_count` |
| 8 | `opened_at` | 개찰일시 | `opened_at` |

### 예시

원문:

```text
[1^한신정보주식회사^6098141001^정상진^108878780^88.041^38^2016-03-07 12:00]
```

정규화 결과 예시:

```json
{
  "seq_no": 1,
  "winner_company_name": "한신정보주식회사",
  "winner_business_no": "6098141001",
  "representative_name": "정상진",
  "award_amount": 108878780,
  "award_rate": 88.041,
  "bidder_count": 38,
  "opened_at": "2016-03-07 12:00",
  "raw_item_text": "[1^한신정보주식회사^6098141001^정상진^108878780^88.041^38^2016-03-07 12:00]"
}
```

## 5. `cntrctInfoList` 파싱 규칙

### 원문 형식

```text
[순번^계약번호^계약명^계약기관명^계약수요기관명^계약체결방법명^계약금액^계약일자]
```

### 필드 매핑

| 순서 | 필드명 | 설명 | 저장 컬럼 |
|---|---|---|---|
| 1 | `seq_no` | 순번 | `seq_no` |
| 2 | `contract_no` | 계약번호 | `contract_no` |
| 3 | `contract_name` | 계약명 | `contract_name` |
| 4 | `contract_instt_nm` | 계약기관명 | `contract_instt_nm` |
| 5 | `contract_dminstt_nm` | 계약수요기관명 | `contract_dminstt_nm` |
| 6 | `contract_method_name` | 계약체결방법명 | `contract_method_name` |
| 7 | `contract_amount` | 계약금액 | `contract_amount` |
| 8 | `contract_date` | 계약일자 | `contract_date` |

### 예시

원문:

```text
[1^2016031744700^인터넷운영 가상화시스템 구입^경상남도 창원시^경상남도 창원시^제한경쟁^108878780^2016-03-09]
```

정규화 결과 예시:

```json
{
  "seq_no": 1,
  "contract_no": "2016031744700",
  "contract_name": "인터넷운영 가상화시스템 구입",
  "contract_instt_nm": "경상남도 창원시",
  "contract_dminstt_nm": "경상남도 창원시",
  "contract_method_name": "제한경쟁",
  "contract_amount": 108878780,
  "contract_date": "2016-03-09",
  "raw_item_text": "[1^2016031744700^인터넷운영 가상화시스템 구입^경상남도 창원시^경상남도 창원시^제한경쟁^108878780^2016-03-09]"
}
```

## 6. 아이템 분리 규칙

### 기본 규칙

- 전체 문자열 양끝 공백을 제거한다.
- 빈값이면 빈 리스트 반환
- 문자열이 `[`로 시작하고 `]`로 끝나는지 우선 확인한다.
- 다건 데이터는 `],[` 경계를 우선 기준으로 분리한다.

예시:

```text
[1^...],[2^...]
```

분리 결과:

- `[1^...]`
- `[2^...]`

### 정규화 전처리

- 줄바꿈은 공백 1개로 치환한다.
- 연속 공백은 1개로 축약한다.
- item 단위 파싱 전 양끝 대괄호는 제거하되 `raw_item_text`에는 원문 그대로 남긴다.

## 7. 타입 변환 규칙

### 숫자형

- `seq_no`, `bidder_count` -> 정수 변환 시도
- `award_amount`, `contract_amount` -> 정수 또는 decimal 변환 시도
- `award_rate` -> float 또는 decimal 변환 시도

변환 실패 시:

- 원문 유지
- 정규화 컬럼은 `null`
- 파싱 경고 로그 기록

### 날짜형

- `opened_at` 형식 예상: `YYYY-MM-DD HH:MM`
- `contract_date` 형식 예상: `YYYY-MM-DD`

변환 실패 시:

- 원문 유지
- 날짜 컬럼은 문자열 그대로 보조 저장하거나 `null`
- 파서 로그에 원문과 필드 위치 기록

## 8. 빈값 처리 규칙

다음은 모두 빈값으로 본다.

- `""`
- `null`
- `[]`
- `<bidwinrInfoList />`
- `<cntrctInfoList />`

해석 규칙:

- `bidwinrInfoList` 빈값: 아직 낙찰 전이거나 낙찰 정보 미공개 가능성
- `cntrctInfoList` 빈값: 아직 계약 전이거나 계약 정보 미공개 가능성
- 따라서 상태 미도달과 파싱 실패를 구분해야 한다.

## 9. 오류 허용 전략

### 권장 정책

- 개별 item 파싱 실패는 전체 응답 실패로 처리하지 않는다.
- item 일부 필드 누락 시 가능한 필드만 부분 저장한다.
- 예상 필드 수보다 많으면 초과 필드는 `raw_item_text`로만 보존한다.
- 예상 필드 수보다 적으면 누락 필드는 `null`로 채운다.

### 최소 로그 항목

- `source_api_name`
- `operation_name`
- `business_type`
- `contract_process_id`
- `field_name`
- `raw_item_text`
- `error_message`

## 10. 내부 저장 전략

### 원문 보존

- `contract_process_integrations.bidwinr_info_list_raw`
- `contract_process_integrations.cntrct_info_list_raw`

### 정규화 테이블

- `contract_process_awards`
- `contract_process_contracts`

### 화면용 활용

- 낙찰자정보는 상세 화면, 분석 화면, 타임라인 상태 판정에 활용
- 계약정보는 계약 단계 표시, 계약기관/금액 분석, 완료 상태 판정에 활용

## 11. 파싱 우선순위 권장안

1. 원문 저장
2. item 리스트 분리
3. 필드 개수 검증
4. 타입 변환 시도
5. 정규화 테이블 반영
6. 타임라인 단계 스냅샷 생성

## 12. 설계상 결정 사항

- 설계 단계에서는 정규표현식 하나로 전부 해결하려 하지 않는다.
- item 분리와 필드 분리를 분리한 2단계 파서를 권장한다.
- 파싱 결과보다 원문 보존이 우선이다.
- 후속 운영에서 예외 케이스가 쌓이면 규칙 문서를 갱신하는 방식으로 관리한다.
