from abc import ABC, abstractmethod


class OperationRepository(ABC):
    @abstractmethod
    def list_operations(self) -> list[dict[str, str]]:
        raise NotImplementedError
