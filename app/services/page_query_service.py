from app.repositories import PageRepository, SamplePageRepository


class PageQueryService:
    def __init__(self, repository: PageRepository | None = None) -> None:
        self.repository = repository or SamplePageRepository()

    def list_prespecs(
        self,
        *,
        q: str | None = None,
        stage: str | None = None,
        business_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, str]]:
        return self.repository.list_prespecs(
            q=q,
            stage=stage,
            business_type=business_type,
            date_from=date_from,
            date_to=date_to,
        )

    def list_results(self) -> list[dict[str, str]]:
        return self.repository.list_results()

    def list_operations(self) -> list[dict[str, str]]:
        return self.repository.list_operations()
