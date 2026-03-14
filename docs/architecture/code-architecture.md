# Code Architecture

## 1. 목적

- 본 문서는 현재 코드베이스의 계층 구조와 책임 분리를 정리한다.
- 설계 문서와 실제 코드 구조가 어떻게 연결되는지 설명한다.

## 2. 현재 구조

```text
app/
  config.py
  db.py
  main.py
  models/
  sample_data/
    bids.py
    pages.py
  repositories/
    bid_repository.py
    sample_bid_repository.py
    page_repository.py
    sample_page_repository.py
  services/
    bid_query_service.py
    page_query_service.py
  presentation/
    mappers/
      bid_mapper.py
      page_mapper.py
      secondary_page_mapper.py
    viewmodels/
      bids.py
      dashboard.py
      timeline.py
      pages.py
      prespecs.py
      results.py
      favorites.py
      operations.py
templates/
tests/
```

## 3. 계층별 책임

### `sample_data/`

- 초기 화면 검증용 샘플 원본 데이터 보관
- 실제 DB 연결 전까지 repository의 backing source 역할

### `repositories/`

- 데이터 접근 인터페이스 제공
- 현재는 `Sample*Repository` 구현체 사용
- 이후 `SqlModel*Repository`로 교체 가능

### `services/`

- 화면/도메인 기준 조회 조립
- 라우트가 데이터 소스 세부사항을 직접 알지 않게 함

### `presentation/mappers/`

- raw data -> view-model 변환
- 날짜/상태/구조를 템플릿 친화적으로 정리

### `presentation/viewmodels/`

- 화면 전용 데이터 모델
- 메인 화면과 보조 화면을 분리해 관리

### `templates/`

- Bootstrap 5 + Jinja2 + HTMX 렌더링 계층
- page template + partial 구조

### `main.py`

- FastAPI 라우트
- 페이지 컨텍스트 조립
- 템플릿 응답 반환

## 4. 데이터 흐름

```text
sample_data
  -> repository
  -> service
  -> mapper
  -> view-model
  -> template
```

향후 목표:

```text
database / external api
  -> repository
  -> service
  -> mapper
  -> view-model
  -> template
```

## 5. 현재 상태 요약

- 메인/보조 화면 모두 view-model 기반으로 렌더링
- repository/service 분리 완료
- 샘플 데이터로 UI 검증 가능
- 테스트로 기본 렌더링과 mapper 검증 가능

## 6. 다음 확장 방향

1. `SqlModelBidRepository` 추가
2. 보조 화면용 DB repository 확장
3. sample_data 의존도를 줄이고 실제 DB 조회로 전환
4. partial 응답도 더 세분화된 mapper 계층 사용
