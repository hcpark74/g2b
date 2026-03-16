def get_sample_prespecs() -> list[dict[str, str]]:
    return [
        {
            "stage": "사전규격",
            "business_type": "용역",
            "title": "2026년 중소기업 인력지원사업 종합관리시스템 유지보수 용역",
            "key": "R26BD00019757",
            "org": "조달청 경남지방조달청",
            "demand_org": "중소벤처기업진흥공단",
            "date": "2026-03-10",
            "linked_bid": "연결됨",
            "linked_bid_variant": "success",
            "linked_bid_id": "R26BK00000001-000",
        },
        {
            "stage": "발주계획",
            "business_type": "공사",
            "title": "지방도 840호선 국영읍 신기 노후포장 보수공사",
            "key": "R26DD00030001",
            "org": "전라남도",
            "demand_org": "전라남도",
            "date": "2026-02-25",
            "linked_bid": "연결됨",
            "linked_bid_variant": "success",
            "linked_bid_id": "R26BK00000003-000",
        },
        {
            "stage": "조달요청",
            "business_type": "물품",
            "title": "전남소방본부 구급소모품 구매",
            "key": "R26DC00020011",
            "org": "전라남도",
            "demand_org": "전라남도 소방본부",
            "date": "2026-03-11",
            "linked_bid": "검토중",
            "linked_bid_variant": "warning",
            "linked_bid_id": "",
        },
    ]


def get_sample_results() -> list[dict[str, str]]:
    return [
        {
            "bid_no": "R26BK00000011-000",
            "title": "AI 기반 민원 분석 시스템 구축 용역",
            "business_type": "용역",
            "status": "낙찰",
            "status_variant": "success",
            "version_label": "정정공고",
            "version_variant": "primary",
            "winner": "우리소프트",
            "award_amount": "428,000,000",
            "award_rate": "89.12%",
            "contract_amount": "430,000,000",
            "contract_date": "2026-02-28",
            "contract_name": "민원 분석 시스템 구축 계약",
            "notice_org": "조달청",
            "demand_org": "경기도청",
        },
        {
            "bid_no": "R26BK00000012-000",
            "title": "스마트 보관함 구매",
            "business_type": "물품",
            "status": "투찰완료",
            "status_variant": "success",
            "version_label": "최초공고",
            "version_variant": "secondary",
            "winner": "한빛솔루션",
            "award_amount": "91,000,000",
            "award_rate": "87.99%",
            "contract_amount": "91,000,000",
            "contract_date": "2026-03-03",
            "contract_name": "스마트 보관함 공급 계약",
            "notice_org": "강원지방조달청",
            "demand_org": "강원랜드",
        },
    ]


def get_sample_operations() -> list[dict[str, str]]:
    return [
        {
            "job_type": "daily_sync",
            "target": "입찰공고정보서비스",
            "status": "completed",
            "started_at": "2026-03-12 06:00:00",
            "finished_at": "2026-03-12 06:04:12",
            "message": "신규 공고 12건, 변경 공고 5건 반영",
        },
        {
            "job_type": "bid_resync",
            "target": "R26BK00000001-000",
            "status": "running",
            "started_at": "2026-03-12 19:41:20",
            "finished_at": "-",
            "message": "계약과정통합공개 타임라인 재수집 중",
        },
        {
            "job_type": "industry_sync",
            "target": "업종 및 근거법규서비스",
            "status": "failed",
            "started_at": "2026-03-12 04:10:00",
            "finished_at": "2026-03-12 04:11:03",
            "message": "일시적 HTTP Error, 재시도 대기",
        },
    ]
