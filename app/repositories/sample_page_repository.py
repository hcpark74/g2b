from app.repositories.page_repository import PageRepository
from app.sample_data import get_sample_prespecs, get_sample_results


class SamplePageRepository(PageRepository):
    def list_prespecs(self) -> list[dict[str, str]]:
        return get_sample_prespecs()

    def list_results(self) -> list[dict[str, str]]:
        return get_sample_results()
