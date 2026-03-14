from app.repositories.operation_repository import OperationRepository
from app.sample_data import get_sample_operations


class SampleOperationRepository(OperationRepository):
    def list_operations(self) -> list[dict[str, str]]:
        return get_sample_operations()
