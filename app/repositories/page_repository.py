from abc import ABC, abstractmethod


class PageRepository(ABC):
    @abstractmethod
    def list_prespecs(
        self,
        *,
        q: str | None = None,
        stage: str | None = None,
        business_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, str]]:
        raise NotImplementedError

    @abstractmethod
    def list_results(self) -> list[dict[str, str]]:
        raise NotImplementedError
