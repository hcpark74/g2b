# Data Model: SQLite 초안 및 PostgreSQL 확장 전략

## 1. 개요

- 본 문서는 `docs/PRD.md`와 `docs/api/api-spec.md`를 기준으로 초기 SQLite 스키마 초안을 정의한다.
- 목표는 MVP를 빠르게 구현하되, 추후 PostgreSQL로 무리 없이 확장 가능한 구조를 유지하는 것이다.
- 초기 단계에서는 SQLite의 단순성과 배포 편의성을 활용하고, 운영 단계에서는 PostgreSQL의 동시성, 인덱스, JSON 처리 성능을 활용한다.

## 2. 설계 원칙

- 공고의 식별자는 `bid_id = {공고번호}-{차수}` 형식의 문자열을 사용한다.
- API 원본 데이터와 정제 데이터는 분리 저장한다.
- 자주 조회하는 리스트 화면 기준으로 인덱스를 설계한다.
- SQLite에서도 동작하는 컬럼 타입을 우선 사용하되, PostgreSQL 전환 시 확장 포인트를 명시한다.
- 삭제보다는 상태 변경과 타임라인 기록을 우선해 이력 추적성을 확보한다.

## 3. SQLite 기준 테이블 초안

### 3.1 `bids`

- 목적: 공고 리스트와 내부 상태 관리의 중심 테이블

```sql
CREATE TABLE IF NOT EXISTS bids (
    bid_id TEXT PRIMARY KEY,
    bid_no TEXT NOT NULL,
    bid_seq TEXT NOT NULL DEFAULT '00',
    title TEXT NOT NULL,
    demand_org TEXT,
    notice_org TEXT,
    category TEXT,
    status TEXT NOT NULL DEFAULT 'collected',
    posted_at TEXT,
    closed_at TEXT,
    budget_amount INTEGER,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    favorite_memo TEXT,
    source_api_name TEXT,
    view_count INTEGER NOT NULL DEFAULT 0,
    last_synced_at TEXT,
    last_changed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (status IN ('collected', 'reviewing', 'favorite', 'submitted', 'won', 'archived')),
    CHECK (is_favorite IN (0, 1))
);
```

권장 인덱스:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS ux_bids_bid_no_seq ON bids (bid_no, bid_seq);
CREATE INDEX IF NOT EXISTS ix_bids_status_closed_at ON bids (status, closed_at);
CREATE INDEX IF NOT EXISTS ix_bids_demand_org ON bids (demand_org);
CREATE INDEX IF NOT EXISTS ix_bids_notice_org ON bids (notice_org);
CREATE INDEX IF NOT EXISTS ix_bids_posted_at ON bids (posted_at DESC);
CREATE INDEX IF NOT EXISTS ix_bids_closed_at ON bids (closed_at ASC);
CREATE INDEX IF NOT EXISTS ix_bids_budget_amount ON bids (budget_amount);
CREATE INDEX IF NOT EXISTS ix_bids_is_favorite ON bids (is_favorite, updated_at DESC);
```

설명:

- `bid_id`는 앱 내부 PK로 사용한다.
- `bid_no + bid_seq` 유니크 인덱스를 추가해 외부 데이터 정합성을 보장한다.
- `posted_at`, `closed_at`는 SQLite에서 `TEXT`로 저장하되 ISO 8601 포맷을 강제하는 것이 좋다.
- `is_favorite`는 SQLite 특성상 `INTEGER(0/1)`로 둔다.

Phase 3 버전 정규화 필드 초안:

```sql
ALTER TABLE bids ADD COLUMN notice_version_type TEXT;
ALTER TABLE bids ADD COLUMN is_latest_version INTEGER NOT NULL DEFAULT 0;
ALTER TABLE bids ADD COLUMN is_effective_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE bids ADD COLUMN parent_bid_id TEXT;
ALTER TABLE bids ADD COLUMN version_reason TEXT;
```

권장 제약 및 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_bids_bid_no_seq_changed ON bids (bid_no, bid_seq DESC, last_changed_at DESC);
CREATE INDEX IF NOT EXISTS ix_bids_bid_no_latest_effective ON bids (bid_no, is_effective_version, bid_seq DESC);
CREATE INDEX IF NOT EXISTS ix_bids_notice_version_type ON bids (notice_version_type);
```

버전 필드 설명:

- `notice_version_type`: `original`, `revision`, `cancellation`, `unknown`
- `is_latest_version`: 같은 `bid_no` 그룹에서 가장 최신 차수인지 여부
- `is_effective_version`: 취소공고가 아닌 실제 검토 대상 차수인지 여부
- `parent_bid_id`: 직전 차수 또는 원공고를 연결하는 참조값
- `version_reason`: 정정/취소 사유 원문 또는 요약

Phase 1 우선순위:

- 1순위: `bid_id`, `status`, `posted_at`, `closed_at`, `is_favorite`
- 2순위: `bid_no + bid_seq`, `notice_org`, `demand_org`
- 3순위: `budget_amount` 및 후속 분석용 보조 인덱스

Phase 3 버전 정규화 우선순위:

- 1순위: `notice_version_type`, `is_effective_version`
- 2순위: `is_latest_version`, `parent_bid_id`
- 3순위: `version_reason`

### 3.2 `bid_details`

- 목적: 공고 상세 본문, API 원본, 크롤링 보강 데이터 저장

```sql
CREATE TABLE IF NOT EXISTS bid_details (
    bid_id TEXT PRIMARY KEY,
    description_text TEXT,
    raw_api_data TEXT,
    crawl_data TEXT,
    detail_hash TEXT,
    collected_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_bid_details_collected_at ON bid_details (collected_at DESC);
CREATE INDEX IF NOT EXISTS ix_bid_details_detail_hash ON bid_details (detail_hash);
```

설명:

- `raw_api_data`, `crawl_data`는 SQLite에서는 `TEXT(JSON string)`로 저장한다.
- `detail_hash`는 상세 내용 변경 감지에 사용한다.

Phase 1 우선순위:

- 1순위: `bid_id`
- 2순위: `collected_at`, `detail_hash`

### 3.2.a `bid_version_changes` (Phase 3 초안)

- 목적: 변경이력 API의 전후값을 버전 단위로 저장

```sql
CREATE TABLE IF NOT EXISTS bid_version_changes (
    change_id TEXT PRIMARY KEY,
    bid_id TEXT NOT NULL,
    bid_no TEXT NOT NULL,
    bid_seq TEXT NOT NULL,
    change_item_name TEXT NOT NULL,
    before_value TEXT,
    after_value TEXT,
    changed_at TEXT,
    source_api_name TEXT NOT NULL,
    raw_data TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_bid_version_changes_bid_id_changed_at ON bid_version_changes (bid_id, changed_at DESC);
CREATE INDEX IF NOT EXISTS ix_bid_version_changes_bid_no_seq ON bid_version_changes (bid_no, bid_seq);
CREATE INDEX IF NOT EXISTS ix_bid_version_changes_item_name ON bid_version_changes (change_item_name);
```

설명:

- `getBidPblancListInfoChgHstry*` 응답을 정규화 저장하는 테이블이다.
- `history`와 `timeline`에 원문 변경 항목을 연결할 때 사용한다.
- SQLite에서는 `raw_data`를 `TEXT(JSON string)`로 유지하고 PostgreSQL 전환 시 `JSONB`로 바꾸는 것이 적절하다.

### 3.3 `attachments`

- 목적: 첨부파일 메타데이터 및 저장 경로 관리

```sql
CREATE TABLE IF NOT EXISTS attachments (
    attachment_id TEXT PRIMARY KEY,
    bid_id TEXT NOT NULL,
    name TEXT NOT NULL,
    file_type TEXT,
    download_url TEXT,
    local_path TEXT,
    file_size INTEGER,
    content_hash TEXT,
    collected_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_attachments_bid_id ON attachments (bid_id);
CREATE INDEX IF NOT EXISTS ix_attachments_file_type ON attachments (file_type);
CREATE INDEX IF NOT EXISTS ix_attachments_collected_at ON attachments (collected_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS ux_attachments_bid_name_url ON attachments (bid_id, name, download_url);
```

설명:

- 동일 공고 내 동일 파일이 중복 저장되지 않도록 `(bid_id, name, download_url)` 유니크 인덱스를 둔다.
- 실제 파일 저장은 로컬 디스크 또는 오브젝트 스토리지로 분리 가능하다.

Phase 1 우선순위:

- 1순위: `bid_id`
- 2순위: `collected_at`
- 3순위: `file_type`, `(bid_id, name, download_url)` 유니크 제약

### 3.4 `timeline_logs`

- 목적: 공고 진행 단계와 변경 이력 기록

```sql
CREATE TABLE IF NOT EXISTS timeline_logs (
    timeline_id TEXT PRIMARY KEY,
    bid_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    label TEXT NOT NULL,
    event_status TEXT,
    source TEXT,
    occurred_at TEXT,
    payload TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_timeline_logs_bid_id_occurred_at ON timeline_logs (bid_id, occurred_at ASC);
CREATE INDEX IF NOT EXISTS ix_timeline_logs_stage ON timeline_logs (stage);
```

설명:

- `stage` 예시: `prespec`, `bid_notice`, `bid_open`, `award`, `contract`
- `payload`는 단계별 원본 또는 추가 정보 저장용 JSON 문자열이다.

### 3.5 `favorites`

- 목적: 사용자별 관심 공고 관리

```sql
CREATE TABLE IF NOT EXISTS favorites (
    favorite_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    bid_id TEXT NOT NULL,
    memo TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS ux_favorites_user_bid ON favorites (user_id, bid_id);
CREATE INDEX IF NOT EXISTS ix_favorites_user_id_created_at ON favorites (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_favorites_bid_id ON favorites (bid_id);
```

설명:

- MVP에서 단일 사용자 환경이면 `bids.is_favorite`만으로도 시작 가능하다.
- 다중 사용자 확장을 고려해 `favorites` 테이블은 미리 설계해두는 것이 좋다.

### 3.6 `sync_jobs`

- 목적: 일일 수집 및 수동 재수집 작업 상태 추적

```sql
CREATE TABLE IF NOT EXISTS sync_jobs (
    job_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    bid_id TEXT,
    requested_by TEXT,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE SET NULL
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_sync_jobs_status_created_at ON sync_jobs (status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_sync_jobs_bid_id ON sync_jobs (bid_id);
CREATE INDEX IF NOT EXISTS ix_sync_jobs_job_type ON sync_jobs (job_type);
```

### 3.7 `industry_base_law_rules`

- 목적: 조달청 업종 및 근거법규 서비스의 기준정보 마스터 저장

```sql
CREATE TABLE IF NOT EXISTS industry_base_law_rules (
    industry_rule_id TEXT PRIMARY KEY,
    indstryty_clsfc_cd TEXT NOT NULL,
    indstryty_clsfc_nm TEXT,
    indstryty_cd TEXT NOT NULL,
    indstryty_nm TEXT NOT NULL,
    base_law_name TEXT,
    base_law_article_clause_name TEXT,
    base_law_url TEXT,
    related_regulation_contents TEXT,
    inclsn_lcns_raw TEXT,
    indstryty_use_yn TEXT NOT NULL DEFAULT 'Y',
    indstryty_rgst_dt TEXT,
    indstryty_chg_dt TEXT,
    source_api_name TEXT NOT NULL DEFAULT 'IndstrytyBaseLawrgltInfoService',
    raw_api_data TEXT,
    last_synced_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (indstryty_use_yn IN ('Y', 'N'))
);
```

권장 인덱스:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS ux_industry_base_law_rules_industry_cd ON industry_base_law_rules (indstryty_cd);
CREATE INDEX IF NOT EXISTS ix_industry_base_law_rules_clsfc_cd ON industry_base_law_rules (indstryty_clsfc_cd);
CREATE INDEX IF NOT EXISTS ix_industry_base_law_rules_use_yn ON industry_base_law_rules (indstryty_use_yn);
CREATE INDEX IF NOT EXISTS ix_industry_base_law_rules_chg_dt ON industry_base_law_rules (indstryty_chg_dt DESC);
CREATE INDEX IF NOT EXISTS ix_industry_base_law_rules_nm ON industry_base_law_rules (indstryty_nm);
```

설명:

- `indstryty_cd`는 외부 기준 업종 코드의 핵심 식별자이므로 유니크하게 관리한다.
- `industry_rule_id`는 내부 PK로 두고, 초기에는 `indstryty_cd`와 동일하게 사용해도 무방하다.
- `inclsn_lcns_raw`는 원본 문자열 보관용이다.
- `raw_api_data`는 추후 파싱 오류나 원본 비교를 위한 JSON 문자열 보관용이다.

### 3.8 `industry_inclusion_licenses`

- 목적: `inclsnLcns` 서브데이터셋을 정규화해 제한업종/허용업종 관계를 저장

```sql
CREATE TABLE IF NOT EXISTS industry_inclusion_licenses (
    inclusion_license_id TEXT PRIMARY KEY,
    industry_rule_id TEXT NOT NULL,
    seq_no INTEGER,
    restricted_industry_cd TEXT,
    restricted_industry_nm TEXT,
    allowed_industry_cd TEXT,
    allowed_industry_nm TEXT,
    raw_item_text TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (industry_rule_id) REFERENCES industry_base_law_rules (industry_rule_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_industry_inclusion_licenses_rule_id ON industry_inclusion_licenses (industry_rule_id);
CREATE INDEX IF NOT EXISTS ix_industry_inclusion_licenses_restricted_cd ON industry_inclusion_licenses (restricted_industry_cd);
CREATE INDEX IF NOT EXISTS ix_industry_inclusion_licenses_allowed_cd ON industry_inclusion_licenses (allowed_industry_cd);
CREATE UNIQUE INDEX IF NOT EXISTS ux_industry_inclusion_licenses_rule_seq ON industry_inclusion_licenses (industry_rule_id, seq_no);
```

설명:

- `inclsnLcns`가 비어 있는 응답도 존재하므로 별도 테이블은 선택적으로만 생성된다.
- 원본 포맷이 일정하지 않을 수 있어 `raw_item_text`를 함께 저장하는 것이 안전하다.
- 검색 관점에서는 허용업종 또는 제한업종 코드 기준 역추적이 가능해진다.

### 3.9 `contract_process_integrations`

- 목적: 계약과정통합공개서비스 원본 응답을 공고 단위로 저장하고 사전규격/입찰/낙찰/계약 연결키를 관리

```sql
CREATE TABLE IF NOT EXISTS contract_process_integrations (
    contract_process_id TEXT PRIMARY KEY,
    business_type TEXT NOT NULL,
    inqry_div TEXT NOT NULL,
    bid_id TEXT,
    bid_ntce_no TEXT,
    bid_ntce_ord TEXT,
    bf_spec_rgst_no TEXT,
    order_plan_no TEXT,
    order_plan_unty_no TEXT,
    prcrmnt_req_no TEXT,
    order_biz_nm TEXT,
    order_instt_nm TEXT,
    order_ym TEXT,
    prcrmnt_methd_nm TEXT,
    cntrct_cncls_mthd_nm TEXT,
    bf_spec_biz_nm TEXT,
    bf_spec_dminstt_nm TEXT,
    bf_spec_ntce_instt_nm TEXT,
    opnin_rgst_clse_dt TEXT,
    bid_ntce_nm TEXT,
    bid_dminstt_nm TEXT,
    bid_mthd_nm TEXT,
    bid_ntce_dt TEXT,
    bidwinr_info_list_raw TEXT,
    cntrct_info_list_raw TEXT,
    raw_api_data TEXT,
    last_synced_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (business_type IN ('foreign', 'goods', 'service', 'construction')),
    CHECK (inqry_div IN ('1', '2', '3', '4')),
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE SET NULL
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_contract_process_integrations_bid_id ON contract_process_integrations (bid_id);
CREATE INDEX IF NOT EXISTS ix_contract_process_integrations_bid_ntce_no_ord ON contract_process_integrations (bid_ntce_no, bid_ntce_ord);
CREATE INDEX IF NOT EXISTS ix_contract_process_integrations_bf_spec_rgst_no ON contract_process_integrations (bf_spec_rgst_no);
CREATE INDEX IF NOT EXISTS ix_contract_process_integrations_order_plan_no ON contract_process_integrations (order_plan_no);
CREATE INDEX IF NOT EXISTS ix_contract_process_integrations_order_plan_unty_no ON contract_process_integrations (order_plan_unty_no);
CREATE INDEX IF NOT EXISTS ix_contract_process_integrations_prcrmnt_req_no ON contract_process_integrations (prcrmnt_req_no);
CREATE INDEX IF NOT EXISTS ix_contract_process_integrations_business_type ON contract_process_integrations (business_type);
```

설명:

- 이 테이블은 통합 타임라인의 원본 허브 역할을 한다.
- `bid_id`가 아직 내부 테이블에 없더라도 `bid_ntce_no`, `order_plan_no`, `bf_spec_rgst_no`, `prcrmnt_req_no`만으로 먼저 적재 가능해야 한다.
- `bidwinr_info_list_raw`, `cntrct_info_list_raw`는 정규화 전 원문 보관용이다.

### 3.10 `contract_process_awards`

- 목적: `bidwinrInfoList`를 정규화해 낙찰자 정보 목록을 저장

```sql
CREATE TABLE IF NOT EXISTS contract_process_awards (
    award_id TEXT PRIMARY KEY,
    contract_process_id TEXT NOT NULL,
    seq_no INTEGER,
    winner_company_name TEXT,
    winner_business_no TEXT,
    representative_name TEXT,
    award_amount NUMERIC,
    award_rate REAL,
    bidder_count INTEGER,
    opened_at TEXT,
    raw_item_text TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (contract_process_id) REFERENCES contract_process_integrations (contract_process_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_contract_process_awards_process_id ON contract_process_awards (contract_process_id);
CREATE INDEX IF NOT EXISTS ix_contract_process_awards_business_no ON contract_process_awards (winner_business_no);
CREATE INDEX IF NOT EXISTS ix_contract_process_awards_opened_at ON contract_process_awards (opened_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS ux_contract_process_awards_process_seq ON contract_process_awards (contract_process_id, seq_no);
```

설명:

- 낙찰금액은 초기 SQLite에서는 `NUMERIC` 또는 `TEXT` 전략 중 하나를 택할 수 있으나, 운영 전환을 고려하면 숫자형 보관이 유리하다.
- 낙찰률은 소수점이 포함되므로 `REAL`로 분리 저장한다.

### 3.11 `contract_process_contracts`

- 목적: `cntrctInfoList`를 정규화해 계약 정보 목록을 저장

```sql
CREATE TABLE IF NOT EXISTS contract_process_contracts (
    contract_item_id TEXT PRIMARY KEY,
    contract_process_id TEXT NOT NULL,
    seq_no INTEGER,
    contract_no TEXT,
    contract_name TEXT,
    contract_instt_nm TEXT,
    contract_dminstt_nm TEXT,
    contract_method_name TEXT,
    contract_amount NUMERIC,
    contract_date TEXT,
    raw_item_text TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (contract_process_id) REFERENCES contract_process_integrations (contract_process_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_contract_process_contracts_process_id ON contract_process_contracts (contract_process_id);
CREATE INDEX IF NOT EXISTS ix_contract_process_contracts_contract_no ON contract_process_contracts (contract_no);
CREATE INDEX IF NOT EXISTS ix_contract_process_contracts_contract_date ON contract_process_contracts (contract_date DESC);
CREATE UNIQUE INDEX IF NOT EXISTS ux_contract_process_contracts_process_seq ON contract_process_contracts (contract_process_id, seq_no);
```

설명:

- 하나의 입찰공고에 연결된 계약이 여러 건일 수 있으므로 별도 테이블이 적합하다.
- `contract_no`는 대외 식별자 후보이지만, 누락 가능성을 고려해 내부 PK와 분리한다.

### 3.12 `timeline_stage_snapshots`

- 목적: 통합 타임라인 화면용으로 단계별 스냅샷을 빠르게 조회할 수 있도록 정규화된 요약 레이어를 저장

```sql
CREATE TABLE IF NOT EXISTS timeline_stage_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    bid_id TEXT,
    contract_process_id TEXT,
    stage TEXT NOT NULL,
    stage_label TEXT NOT NULL,
    related_key TEXT,
    occurred_at TEXT,
    status TEXT,
    summary_text TEXT,
    payload TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE CASCADE,
    FOREIGN KEY (contract_process_id) REFERENCES contract_process_integrations (contract_process_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_timeline_stage_snapshots_bid_id_stage ON timeline_stage_snapshots (bid_id, stage);
CREATE INDEX IF NOT EXISTS ix_timeline_stage_snapshots_bid_id_occurred_at ON timeline_stage_snapshots (bid_id, occurred_at ASC);
CREATE INDEX IF NOT EXISTS ix_timeline_stage_snapshots_process_id ON timeline_stage_snapshots (contract_process_id);
```

설명:

- `timeline_logs`가 범용 이벤트 로그라면, 이 테이블은 화면 렌더링과 검색 최적화를 위한 읽기 모델에 가깝다.
- 설계 단계에서는 물리 테이블로 둘지, 뷰 또는 캐시로 둘지 선택 가능하다.

### 3.13 `bid_license_limits`

- 목적: `BidPublicInfoService/getBidPblancListInfoLicenseLimit`의 면허제한정보를 정규화한다.

```sql
CREATE TABLE IF NOT EXISTS bid_license_limits (
    license_limit_id TEXT PRIMARY KEY,
    bid_id TEXT,
    bid_ntce_no TEXT NOT NULL,
    bid_ntce_ord TEXT NOT NULL,
    lmt_grp_no INTEGER,
    lmt_sno INTEGER,
    lcns_lmt_nm TEXT,
    permsn_indstryty_list_raw TEXT,
    indstryty_mfrc_fld_list_raw TEXT,
    bsns_div_nm TEXT,
    rgst_dt TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_bid_license_limits_bid_id ON bid_license_limits (bid_id);
CREATE INDEX IF NOT EXISTS ix_bid_license_limits_bid_no_ord ON bid_license_limits (bid_ntce_no, bid_ntce_ord);
CREATE INDEX IF NOT EXISTS ix_bid_license_limits_group_sno ON bid_license_limits (lmt_grp_no, lmt_sno);
```

설명:

- 자격 검토 자동화에서 중요한 테이블이다.
- `permsnIndstrytyList`, `indstrytyMfrcFldList`는 별도 파싱 규칙 수립 전까지 원문 보존을 우선한다.

### 3.14 `bid_participation_regions`

- 목적: `BidPublicInfoService/getBidPblancListInfoPrtcptPsblRgn`의 참가가능지역정보를 정규화한다.

```sql
CREATE TABLE IF NOT EXISTS bid_participation_regions (
    participation_region_id TEXT PRIMARY KEY,
    bid_id TEXT,
    bid_ntce_no TEXT NOT NULL,
    bid_ntce_ord TEXT NOT NULL,
    lmt_sno INTEGER,
    prtcpt_psbl_rgn_nm TEXT,
    bsns_div_nm TEXT,
    rgst_dt TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_bid_participation_regions_bid_id ON bid_participation_regions (bid_id);
CREATE INDEX IF NOT EXISTS ix_bid_participation_regions_bid_no_ord ON bid_participation_regions (bid_ntce_no, bid_ntce_ord);
CREATE INDEX IF NOT EXISTS ix_bid_participation_regions_name ON bid_participation_regions (prtcpt_psbl_rgn_nm);
```

### 3.15 `bid_purchase_items`

- 목적: 구매대상물품/세부품명/수량/단가/납품조건을 정규화한다.

```sql
CREATE TABLE IF NOT EXISTS bid_purchase_items (
    purchase_item_id TEXT PRIMARY KEY,
    bid_id TEXT,
    bid_ntce_no TEXT NOT NULL,
    bid_ntce_ord TEXT NOT NULL,
    bid_clsfc_no TEXT,
    prdct_sno INTEGER,
    dminstt_cd TEXT,
    dminstt_nm TEXT,
    prdct_clsfc_no TEXT,
    prdct_clsfc_no_nm TEXT,
    dtil_prdct_clsfc_no TEXT,
    dtil_prdct_clsfc_no_nm TEXT,
    prdct_spec_nm TEXT,
    qty NUMERIC,
    unit TEXT,
    uprc NUMERIC,
    dlvr_tmlmt_dt TEXT,
    dlvr_daynum INTEGER,
    dlvr_plce TEXT,
    dlvry_cndtn_nm TEXT,
    ntce_notice_dt TEXT,
    hsk_no TEXT,
    asign_amt NUMERIC,
    asign_amt_crncy TEXT,
    bsns_div_nm TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_bid_purchase_items_bid_id ON bid_purchase_items (bid_id);
CREATE INDEX IF NOT EXISTS ix_bid_purchase_items_bid_no_ord ON bid_purchase_items (bid_ntce_no, bid_ntce_ord);
CREATE INDEX IF NOT EXISTS ix_bid_purchase_items_dtil_prdct_no ON bid_purchase_items (dtil_prdct_clsfc_no);
CREATE INDEX IF NOT EXISTS ix_bid_purchase_items_prdct_clsfc_no ON bid_purchase_items (prdct_clsfc_no);
CREATE INDEX IF NOT EXISTS ix_bid_purchase_items_hsk_no ON bid_purchase_items (hsk_no);
```

설명:

- 물품/용역/외자 계열이 공통 구조를 상당 부분 공유하므로 하나의 정규화 테이블로 설계할 수 있다.
- 외자의 경우 `hsk_no`, `asign_amt`, `asign_amt_crncy`가 의미 있는 필드다.

### 3.16 `bid_base_amounts`

- 목적: 기초금액, 예비가격 범위, 각종 보험료/관리비/A값 항목을 정규화한다.

```sql
CREATE TABLE IF NOT EXISTS bid_base_amounts (
    base_amount_id TEXT PRIMARY KEY,
    bid_id TEXT,
    bid_ntce_no TEXT NOT NULL,
    bid_ntce_ord TEXT NOT NULL,
    bid_clsfc_no TEXT,
    bid_ntce_nm TEXT,
    bssamt NUMERIC,
    bssamt_open_dt TEXT,
    rsrvtn_prce_rng_bgn_rate TEXT,
    rsrvtn_prce_rng_end_rate TEXT,
    evl_bss_amt NUMERIC,
    dfcltydgr_cfcnt REAL,
    etc_gnrlexpns_bss_rate REAL,
    gnrl_mngcst_bss_rate REAL,
    prft_bss_rate REAL,
    lbrcst_bss_rate REAL,
    sfty_mngcst NUMERIC,
    sfty_chck_mngcst NUMERIC,
    rtrfund_non NUMERIC,
    env_cnsrvcst NUMERIC,
    scontrct_payprce_pay_grnty_fee NUMERIC,
    mrfn_health_insrprm NUMERIC,
    npn_insrprm NUMERIC,
    odsn_lngtrmrcpr_insrprm NUMERIC,
    useful_amt NUMERIC,
    inpt_dt TEXT,
    bid_prce_calcl_a_yn TEXT,
    qlty_mngcst NUMERIC,
    qlty_mngcst_a_obj_yn TEXT,
    smkp_amt NUMERIC,
    smkp_amt_yn TEXT,
    raw_api_data TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_bid_base_amounts_bid_id ON bid_base_amounts (bid_id);
CREATE INDEX IF NOT EXISTS ix_bid_base_amounts_bid_no_ord ON bid_base_amounts (bid_ntce_no, bid_ntce_ord);
CREATE INDEX IF NOT EXISTS ix_bid_base_amounts_open_dt ON bid_base_amounts (bssamt_open_dt DESC);
CREATE INDEX IF NOT EXISTS ix_bid_base_amounts_inpt_dt ON bid_base_amounts (inpt_dt DESC);
```

설명:

- `물품/용역/공사` 기초금액 계열과 `A값` 계열을 통합해 저장하는 설계다.
- 업무구분별로 비어 있는 컬럼이 생길 수 있으나, 분석 쿼리 단순화 측면에서 장점이 있다.

### 3.17 `bid_change_histories`

- 목적: 공고 변경이력 및 개찰결과 변경이력을 정규화한다.

```sql
CREATE TABLE IF NOT EXISTS bid_change_histories (
    bid_change_history_id TEXT PRIMARY KEY,
    bid_id TEXT,
    bid_ntce_no TEXT NOT NULL,
    bid_ntce_ord TEXT NOT NULL,
    bid_clsfc_no TEXT,
    bsns_div_nm TEXT,
    chg_data_div_nm TEXT,
    chg_dt TEXT NOT NULL,
    rbid_no TEXT,
    chg_item_nm TEXT,
    bfchg_val TEXT,
    afchg_val TEXT,
    lcns_lmt_cd_rgst_list_raw TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_bid_change_histories_bid_id ON bid_change_histories (bid_id);
CREATE INDEX IF NOT EXISTS ix_bid_change_histories_bid_no_ord ON bid_change_histories (bid_ntce_no, bid_ntce_ord);
CREATE INDEX IF NOT EXISTS ix_bid_change_histories_chg_dt ON bid_change_histories (chg_dt DESC);
CREATE INDEX IF NOT EXISTS ix_bid_change_histories_item ON bid_change_histories (chg_item_nm);
```

설명:

- 내부 알림, 변경 감지, 이력 UI에 직접 활용 가능하다.
- `timeline_logs`와 역할이 겹칠 수 있으므로, 장기적으로는 이벤트 로그와 화면용 변경이력을 구분할지 결정이 필요하다.

### 3.18 `bid_eorder_attachments`

- 목적: e발주 첨부파일과 혁신장터 최종제안요청서 교부 파일을 정규화한다.

```sql
CREATE TABLE IF NOT EXISTS bid_eorder_attachments (
    bid_eorder_attachment_id TEXT PRIMARY KEY,
    bid_id TEXT,
    bid_ntce_no TEXT NOT NULL,
    bid_ntce_ord TEXT NOT NULL,
    atch_sno INTEGER,
    source_type TEXT NOT NULL,
    doc_div_nm TEXT,
    file_name TEXT,
    file_url TEXT,
    iss_dt TEXT,
    bsns_div_nm TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (source_type IN ('eorder', 'ppi_final_rfp')),
    FOREIGN KEY (bid_id) REFERENCES bids (bid_id) ON DELETE CASCADE
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS ix_bid_eorder_attachments_bid_id ON bid_eorder_attachments (bid_id);
CREATE INDEX IF NOT EXISTS ix_bid_eorder_attachments_bid_no_ord ON bid_eorder_attachments (bid_ntce_no, bid_ntce_ord);
CREATE INDEX IF NOT EXISTS ix_bid_eorder_attachments_source_type ON bid_eorder_attachments (source_type);
CREATE INDEX IF NOT EXISTS ix_bid_eorder_attachments_file_url ON bid_eorder_attachments (file_url);
```

설명:

- 일반 공고 첨부와 e발주/혁신장터 첨부를 완전히 같은 테이블에 넣을 수도 있지만, 문서 출처와 접근 방식이 달라 별도 레이어를 두는 편이 관리가 쉽다.

## 4. 조회 패턴 기준 인덱스 요약

- 메인 리스트: `bids(status, closed_at)`, `bids(posted_at)`, `bids(is_favorite, updated_at)`
- 기관 필터: `bids(demand_org)`, `bids(notice_org)`
- 상세 조회: `bid_details(bid_id)`, `attachments(bid_id)`, `timeline_logs(bid_id, occurred_at)`
- 사용자 관심 목록: `favorites(user_id, created_at)`
- 작업 상태 조회: `sync_jobs(status, created_at)`, `sync_jobs(bid_id)`
- 업종 기준정보 조회: `industry_base_law_rules(indstryty_cd)`, `industry_base_law_rules(indstryty_clsfc_cd)`, `industry_base_law_rules(indstryty_use_yn)`
- 포함면허 역조회: `industry_inclusion_licenses(industry_rule_id)`, `industry_inclusion_licenses(restricted_industry_cd)`, `industry_inclusion_licenses(allowed_industry_cd)`
- 계약과정 원본 조회: `contract_process_integrations(bid_ntce_no, bid_ntce_ord)`, `contract_process_integrations(order_plan_no)`, `contract_process_integrations(prcrmnt_req_no)`
- 낙찰자 조회: `contract_process_awards(contract_process_id)`, `contract_process_awards(winner_business_no)`
- 계약목록 조회: `contract_process_contracts(contract_process_id)`, `contract_process_contracts(contract_no)`
- 타임라인 조회: `timeline_stage_snapshots(bid_id, occurred_at)`, `timeline_stage_snapshots(contract_process_id)`
- 면허제한 조회: `bid_license_limits(bid_id)`, `bid_license_limits(bid_ntce_no, bid_ntce_ord)`
- 참가가능지역 조회: `bid_participation_regions(bid_id)`, `bid_participation_regions(prtcpt_psbl_rgn_nm)`
- 구매품목 조회: `bid_purchase_items(bid_id)`, `bid_purchase_items(dtil_prdct_clsfc_no)`
- 기초금액 조회: `bid_base_amounts(bid_id)`, `bid_base_amounts(bssamt_open_dt)`
- 변경이력 조회: `bid_change_histories(bid_id)`, `bid_change_histories(chg_dt)`, `bid_change_histories(chg_item_nm)`
- e발주 첨부 조회: `bid_eorder_attachments(bid_id)`, `bid_eorder_attachments(source_type)`

## 5. SQLite 구현 시 주의사항

### 날짜/시간

- SQLite에는 별도 `TIMESTAMP WITH TIME ZONE` 타입이 없으므로 ISO 8601 문자열로 저장한다.
- 예시: `2026-03-12T09:00:00+09:00`

### JSON 저장

- SQLite MVP 단계에서는 `TEXT` 컬럼에 JSON 문자열을 저장한다.
- 조회 시 애플리케이션 계층에서 직렬화/역직렬화한다.

### 동시성

- SQLite는 다중 쓰기 경쟁에 약하므로 배치 수집과 대량 재수집의 동시 실행 수를 제한한다.
- WAL 모드 사용을 고려한다.

예시:

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
```

## 6. PostgreSQL 확장 전략

### 바로 바뀌는 포인트

- `TEXT` 기반 JSON 저장 컬럼을 `JSONB`로 전환
- 날짜 문자열 컬럼을 `TIMESTAMPTZ`로 전환
- `is_favorite INTEGER`를 `BOOLEAN`으로 전환
- 대규모 검색/분석용 인덱스 추가
- 기준정보 테이블의 문자열 검색과 JSON 원본 검색 강화

### PostgreSQL 권장 타입 매핑

| SQLite | PostgreSQL |
|---|---|
| `TEXT` datetime | `TIMESTAMPTZ` |
| `TEXT` json | `JSONB` |
| `INTEGER` boolean | `BOOLEAN` |
| `INTEGER` count | `INTEGER` or `BIGINT` |
| `TEXT PRIMARY KEY` | `TEXT PRIMARY KEY` 또는 `UUID` |

### PostgreSQL 전환 후 개선 대상

- `bid_details.raw_api_data` -> `JSONB`
- `bid_details.crawl_data` -> `JSONB`
- `timeline_logs.payload` -> `JSONB`
- `industry_base_law_rules.raw_api_data` -> `JSONB`
- `contract_process_integrations.raw_api_data` -> `JSONB`
- `timeline_stage_snapshots.payload` -> `JSONB`
- `bid_base_amounts.raw_api_data` -> `JSONB`
- 필요 시 `GIN` 인덱스로 JSON 검색 최적화
- 기관명/공고명 검색용 `pg_trgm` 확장 고려
- 업종명/법령명 검색용 `pg_trgm` 확장 고려
- 발주사업명/입찰공고명 검색용 `pg_trgm` 확장 고려
- 공고명/참조번호/첨부파일명 검색용 `pg_trgm` 확장 고려

예시:

```sql
CREATE INDEX ix_bid_details_raw_api_data_gin
ON bid_details USING GIN (raw_api_data);
```

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX ix_bids_title_trgm
ON bids USING GIN (title gin_trgm_ops);
```

## 7. 권장 마이그레이션 순서

1. SQLite 기준 스키마를 SQLAlchemy/SQLModel 모델로 먼저 고정한다.
2. Alembic 마이그레이션을 도입한다.
3. 개발 단계에서는 SQLite로 검증한다.
4. 운영 전환 시 PostgreSQL에 동일 스키마를 생성한다.
5. JSON/Timestamp/Boolean 타입을 PostgreSQL 전용 타입으로 승격한다.
6. 운영 트래픽 기준 추가 인덱스를 적용한다.

## 8. MVP 권장 범위

- 우선 생성 테이블:
  - `bids`
  - `bid_details`
  - `attachments`
  - `timeline_logs`
  - `sync_jobs`
- 선택 적용:
  - `favorites`
  - `industry_base_law_rules`
  - `industry_inclusion_licenses`
  - `contract_process_integrations`
  - `contract_process_awards`
  - `contract_process_contracts`
  - `timeline_stage_snapshots`
  - `bid_license_limits`
  - `bid_participation_regions`
  - `bid_purchase_items`
  - `bid_base_amounts`
  - `bid_change_histories`
  - `bid_eorder_attachments`

이유:

- MVP의 핵심 기능은 리스트 조회, 상세 조회, 상태 변경, 수동 재수집이다.
- 다중 사용자 기능이 아직 약하면 `favorites`는 2차 도입으로 미뤄도 된다.
- 업종/근거법규 기준정보는 입찰 자격 검토 자동화에 필요하면 MVP 후반 또는 2차 단계에 도입하면 된다.
- 계약과정통합공개 데이터는 PRD의 통합 타임라인 핵심 소스이므로, 상세 화면/분석 화면 우선순위에 따라 MVP 후반 또는 2차 단계의 최우선 후보로 본다.
- `BidPublicInfoService` 기반 상세 정규화 테이블은 운영 핵심이므로, 최소한 `bid_license_limits`, `bid_participation_regions`, `bid_purchase_items`, `bid_change_histories`는 2차 설계 우선순위가 높다.

## 9. SQLModel 설계 팁

- 모델 필드는 SQLite와 PostgreSQL 모두 호환되는 공통 타입으로 우선 선언한다.
- JSON 필드는 초기에는 `str | None` 또는 직렬화 헬퍼를 사용한다.
- PostgreSQL 전환 시 SQLAlchemy dialect 타입으로 `JSONB`를 주입하는 방식이 깔끔하다.
- `created_at`, `updated_at`, `last_synced_at`는 전 테이블 공통 믹스인으로 관리하는 것이 좋다.

## 10. 다음 단계 제안

- `database.py` 또는 `models/` 구조 기준으로 SQLModel 엔티티 초안 작성
- Alembic 초기 마이그레이션 생성
- SQLite seed 데이터와 테스트 조회 쿼리 작성
