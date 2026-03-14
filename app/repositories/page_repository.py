from abc import ABC, abstractmethod


class PageRepository(ABC):
    @abstractmethod
    def list_prespecs(self) -> list[dict[str, str]]:
        raise NotImplementedError

    @abstractmethod
    def list_results(self) -> list[dict[str, str]]:
        raise NotImplementedError
