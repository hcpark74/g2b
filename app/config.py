from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "g2b"
    app_env: str = "development"
    debug: bool = True

    database_url: str = "sqlite:///./g2b.db"
    bid_data_backend: str = "auto"
    admin_sync_token: str = "dev-admin-token"
    job_log_retention_days: int = 30
    ops_slack_webhook_url: str = ""
    ops_health_recent_failure_hours: int = 24

    g2b_api_service_key_encoded: str = ""
    g2b_api_service_key_decoded: str = ""
    g2b_api_bid_public_info_base_url: str = (
        "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
    )
    g2b_api_industry_base_url: str = (
        "https://apis.data.go.kr/1230000/ao/IndstrytyBaseLawrgltInfoService"
    )
    g2b_api_contract_process_base_url: str = (
        "https://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService"
    )

    playwright_user_data_dir: str = ".playwright/g2b-session"
    playwright_headless: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
