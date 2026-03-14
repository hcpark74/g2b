# External API: G2B Bid Public Info Service

## 1. 개요

- 목적: 나라장터 입찰공고의 목록, 검색, 기초금액, 변경이력, 면허제한, 참가가능지역, 구매대상물품, 첨부파일 등 운영 핵심 데이터를 제공한다.
- 서비스 ID: `BidPublicInfoService`
- 서비스명: 나라장터 입찰공고정보서비스
- Base URL: `https://apis.data.go.kr/1230000/ad/BidPublicInfoService`
- 방식: `REST(GET)`
- 포맷: `XML`, `JSON`
- 서비스 버전: 문서상 `3.1`
- 데이터 갱신주기: 수시
- 평균 응답시간: 약 `500ms`
- 최대 트랜잭션: `30 tps`

핵심 판단:

- 이 서비스는 전체 시스템의 운영 중심 HUB로 보는 것이 맞다.
- 메인 리스트, 기본 상세, 공고 상태, 마감일, 기관 정보, 첨부 URL, 일부 자격/가격 판단의 출발점이 된다.

## 2. 왜 이 서비스가 핵심인가

- 대부분의 업무가 `bidNtceNo` 기준으로 시작된다.
- 메인 대시보드 리스트를 이 서비스로 직접 구성할 수 있다.
- `bfSpecRgstNo`, `orderPlanUntyNo`, `untyNtceNo`, `prcrmntReqNo` 같은 연결 키를 확보할 수 있다.
- 후속 API인 `계약과정통합공개서비스`, `낙찰정보서비스`, `계약정보서비스`를 연결하는 중심축이 된다.

## 3. 오퍼레이션 구조 재분류

원문에는 25개 오퍼레이션이 있으나, 설계 관점에서는 아래 7개 그룹으로 보는 것이 효율적이다.

### 그룹 A. 기본 목록 조회

- `getBidPblancListInfoCnstwk`
- `getBidPblancListInfoServc`
- `getBidPblancListInfoFrgcpt`
- `getBidPblancListInfoThng`
- `getBidPblancListInfoEtc`

역할:

- 업무구분별 입찰공고 기본 목록/기본 상세 조회
- 내부 `bids` 마스터의 1차 원천 데이터

### 그룹 B. 검색조건 기반 목록 조회

- `getBidPblancListInfoCnstwkPPSSrch`
- `getBidPblancListInfoServcPPSSrch`
- `getBidPblancListInfoFrgcptPPSSrch`
- `getBidPblancListInfoThngPPSSrch`
- `getBidPblancListInfoEtcPPSSrch`

역할:

- 기간, 기관, 지역, 업종, 가격 등 조건으로 검색용 목록 구성
- 내부 고급 필터 UI 또는 사전 수집 범위 축소에 적합

### 그룹 C. 기초금액 조회

- `getBidPblancListInfoThngBsisAmount`
- `getBidPblancListInfoCnstwkBsisAmount`
- `getBidPblancListInfoServcBsisAmount`

역할:

- 기초금액, 예비가격 범위, 평가기준금액, A값 관련 정보 확보
- 투찰 전략 및 가격 분석 보조

### 그룹 D. 변경이력 조회

- `getBidPblancListInfoChgHstryThng`
- `getBidPblancListInfoChgHstryCnstwk`
- `getBidPblancListInfoChgHstryServc`

역할:

- 공고의 변경 항목과 변경 전후값 추적
- 변경 감지 및 내부 히스토리 로그 보강

### 그룹 E. 자격/지역/주력분야 조회

- `getBidPblancListInfoLicenseLimit`
- `getBidPblancListInfoPrtcptPsblRgn`
- `getBidPblancListEvaluationIndstrytyMfrcInfo`

역할:

- 면허제한, 참가가능지역, 평가대상 주력분야 정보 확보
- 참가 가능성/자격 판단 보조

### 그룹 F. 구매대상물품 조회

- `getBidPblancListInfoThngPurchsObjPrdct`
- `getBidPblancListInfoServcPurchsObjPrdct`
- `getBidPblancListInfoFrgcptPurchsObjPrdct`

역할:

- 구매대상 세부품명, 규격, 수량, 단위, 단가, 납품 조건 확보
- 품목 단위 분석 및 상세 화면 보강

### 그룹 G. 첨부/특수 파일 조회

- `getBidPblancListInfoEorderAtchFileInfo`
- `getBidPblancListPPIFnlRfpIssAtchFileInfo`
- `getBidPblancListBidPrceCalclAInfo`

역할:

- e발주 첨부파일
- 혁신장터 최종제안요청서 첨부파일
- 입찰가격산식 A값 상세 항목 확보

## 4. 설계상 우선 채택 오퍼레이션

### MVP 1차

- `getBidPblancListInfoCnstwk`
- `getBidPblancListInfoServc`
- `getBidPblancListInfoFrgcpt`
- `getBidPblancListInfoThng`

이유:

- 업무구분별 기본 목록만으로도 메인 리스트를 구성할 수 있다.
- `inqryDiv=1/2/3` 구조가 단순하고 운영 이해가 쉽다.

### MVP 2차

- `getBidPblancListInfoLicenseLimit`
- `getBidPblancListInfoPrtcptPsblRgn`
- `getBidPblancListInfoEorderAtchFileInfo`
- `getBidPblancListInfoThngPurchsObjPrdct`
- `getBidPblancListInfoServcPurchsObjPrdct`
- `getBidPblancListInfoFrgcptPurchsObjPrdct`

이유:

- 상세 Drawer 고도화와 자격 검토에 직접 도움된다.

### 3차 고도화

- `getBidPblancListInfo*PPSSrch` 계열
- `getBidPblancListInfo*BsisAmount` 계열
- `getBidPblancListInfoChgHstry*` 계열
- `getBidPblancListBidPrceCalclAInfo`
- `getBidPblancListEvaluationIndstrytyMfrcInfo`

이유:

- 운영보다는 검색 정밀도, 분석, 가격 산정, 공사 심사 판단 고도화에 가깝다.

## 5. 공통 요청 패턴

### 기본 목록 조회 계열

공통 파라미터:

- `ServiceKey` 또는 `serviceKey`
- `pageNo`
- `numOfRows`
- `type=json`
- `inqryDiv`

`inqryDiv` 의미:

- `1`: 등록일시 조회
- `2`: 입찰공고번호 조회
- `3`: 변경일시 조회

조건부 파라미터:

- `inqryBgnDt`, `inqryEndDt`: `inqryDiv=1,3`일 때 필수
- `bidNtceNo`: `inqryDiv=2`일 때 필수

### 검색조건 조회 계열

공통 파라미터:

- `inqryDiv=1` 공고게시일시
- `inqryDiv=2` 개찰일시
- 기간 범위 + 공고명/기관명/업종/가격/지역 등 다수 필터

설계 메모:

- 내부 검색 화면은 이 계열을 바로 사용자 입력마다 호출하기보다, 배치 수집 범위를 좁히는 용도 또는 관리자 검색용으로 두는 것이 안정적이다.

## 6. 핵심 응답 필드 그룹

### 공고 식별/연결 키

- `bidNtceNo`
- `bidNtceOrd`
- `untyNtceNo`
- `bfSpecRgstNo`
- `orderPlanUntyNo`
- `refNo`

### 기본 운영 필드

- `bidNtceNm`
- `ntceKindNm`
- `rgstTyNm`
- `bidNtceDt`
- `bidBeginDt`
- `bidClseDt`
- `opengDt`
- `ntceInsttNm`
- `dminsttNm`
- `bidMethdNm`
- `cntrctCnclsMthdNm`

### 금액/가격 필드

- `bdgtAmt` 또는 `asignBdgtAmt`
- `presmptPrce`
- `VAT`
- `govsplyAmt`
- `bssamt`
- `sucsfbidLwltRate`

### 자격/제한 필드

- `indstrytyLmtYn`
- `bidPrtcptLmtYn`
- `cmmnSpldmdMethdCd`
- `cmmnSpldmdMethdNm`
- `rgnLmtBidLocplcJdgmBssCd`
- `rgnLmtBidLocplcJdgmBssNm`

### 상세/첨부 필드

- `bidNtceDtlUrl`
- `bidNtceUrl`
- `ntceSpecDocUrl1..10`
- `ntceSpecFileNm1..10`
- `stdNtceDocUrl`

### 분석/고도화 필드

- `sucsfbidMthdCd`
- `sucsfbidMthdNm`
- `techAbltEvlRt`
- `bidPrceEvlRt`
- `pubPrcrmntClsfcNo`
- `pubPrcrmntClsfcNm`

## 7. 내부 DB 관점 매핑

### `bids`에 우선 적재할 필드

- `bidNtceNo`, `bidNtceOrd`
- `bidNtceNm`
- `ntceInsttNm`, `dminsttNm`
- `ntceKindNm`, `rgstTyNm`
- `bidNtceDt`, `bidBeginDt`, `bidClseDt`, `opengDt`
- `cntrctCnclsMthdNm`, `bidMethdNm`
- `presmptPrce`, `bdgtAmt`, `VAT`
- `bfSpecRgstNo`, `orderPlanUntyNo`, `untyNtceNo`
- `indstrytyLmtYn`
- `bidNtceDtlUrl`, `bidNtceUrl`
- `rgstDt`, `chgDt`

### 별도 정규화 권장 데이터

- 면허제한정보
- 참가가능지역정보
- 구매대상물품목록
- 기초금액/A값 상세
- 변경이력
- 첨부파일 정보

## 8. 번호체계 해석 메모

- 차세대 번호체계는 `R + 연도(2) + 단계구분(2) + 순번(8)` 형식으로 보인다.
- 문서상 단계구분 예시:
  - `BK`: 입찰
  - `TA`: 계약
  - `DD`: 발주계획
  - `BD`: 사전규격

설계 메모:

- 번호 접두부만으로도 어느 단계 데이터인지 추정 가능하므로 내부 링크 분석에 도움된다.
- 다만 실제 운영에서는 문자열 규칙을 절대 가정하지 말고 원문도 함께 저장해야 한다.

## 9. 원문 문서에서 주의할 점

- 문서가 매우 길고 업무구분별로 필드가 조금씩 다르다.
- `물품`, `용역`, `공사`, `외자`, `기타`는 공통 필드가 많지만 일부 전용 필드가 존재한다.
- 일부 필드는 문서 표기와 실제 응답 포맷이 다를 수 있다.
- `ServiceKey`와 `serviceKey` 표기가 혼용될 수 있다.
- 동일 필드라도 빈 문자열, 누락, `N/A`가 섞여 내려올 수 있다.

## 10. 설계 결론

- 이 서비스는 시스템의 기본틀을 잡는 데 가장 적합하다.
- 먼저 이 서비스 기준으로 `bids` 마스터와 메인 리스트를 설계하는 것이 맞다.
- 이후 `계약과정통합공개서비스`, `낙찰정보서비스`, `계약정보서비스`로 생애주기를 보강하는 구조가 가장 안정적이다.

## 11. 후속 문서화 권장

- `docs/data/data-model.md`에 입찰공고 상세 정규화 테이블 보강
- `docs/api/api-sync-strategy.md`에 `BidPublicInfoService` 우선 수집 전략 반영
- 필요 시 아래 세부 문서로 추가 분리
  - `external-g2b-bid-public-info-list.md`
  - `external-g2b-bid-public-info-search.md`
  - `external-g2b-bid-public-info-amount.md`
  - `external-g2b-bid-public-info-changes.md`
