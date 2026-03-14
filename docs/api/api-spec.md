# API Spec Index

API 문서는 길어지는 것을 방지하기 위해 도메인별로 분리한다.

## 문서 목록

- `docs/api/overview.md`: 공통 규칙, 인증, 응답 형식, 구현 우선순위
- `docs/api/internal-bids.md`: 내부 입찰 관리 API
- `docs/api/external-g2b-bid-public-info.md`: 조달청 입찰공고정보서비스 외부 연동 명세
- `docs/api/external-g2b-industry.md`: 조달청 업종 및 근거법규 외부 연동 명세
- `docs/api/external-g2b-contract-process.md`: 조달청 계약과정통합공개 외부 연동 명세
- `docs/data/parsing/contract-process-subdatasets.md`: 계약과정통합공개 서브데이터셋 파싱 규칙

## 운영 원칙

- 내부 API와 외부 연동 명세를 분리한다.
- HTMX 파셜과 JSON API는 역할을 분리한다.
- 신규 외부 API는 서비스별 개별 문서로 추가한다.
