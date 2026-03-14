from app.repositories import PageRepository, SamplePageRepository


class PageQueryService:
    def __init__(self, repository: PageRepository | None = None) -> None:
        self.repository = repository or SamplePageRepository()

    def list_prespecs(self) -> list[dict[str, str]]:
        return self.repository.list_prespecs()

    def list_results(self) -> list[dict[str, str]]:
        return self.repository.list_results()

    def list_operations(self) -> list[dict[str, str]]:
        return self.repository.list_operations()
