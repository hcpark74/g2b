from app.repositories import OperationRepository, SampleOperationRepository


class OperationQueryService:
    def __init__(self, repository: OperationRepository | None = None) -> None:
        self.repository = repository or SampleOperationRepository()

    def list_operations(self) -> list[dict[str, str]]:
        return self.repository.list_operations()
